---
title: "ADR-0004: Tenant DNS Publication"
weight: 4
---

# ADR-0004: Tenant DNS Publication

|  |  |
|--|--|
| **Status** | Accepted |
| **Date** | 2026-09-01 |
| **Scope** | How a tenant's own DNS records reach the resolver substrate clients use |
| **Depends on** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/), [ADR-0002: Tenant Fabric Numbering](/docs/architecture/decisions/0002-tenant-fabric-numbering/) |
| **Extended by** | [ADR-0005: Tenant Zone Apex Ownership](/docs/architecture/decisions/0005-tenant-zone-apex-ownership/) — the zone apex, which §4 does not assign |
| **Extended by** | [ADR-0006: Tenant Code Boundary](/docs/architecture/decisions/0006-tenant-code-boundary/) — where the tenant's code lives, which §5 does not say |

---

## Context

Seam 2 of [ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) splits addressing
from naming: IPAM belongs to the fabric, while DNS is **tenant-owned but published to the substrate
zone**. With [ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/)
closing egress, this is the last part of the tenant contract still undecided.

### What is already settled

- **Naming.** A tenant's zone is `tenant.site.deevnet.net`; records are
  `service.tenant.site.deevnet.net`. So `grooveiq.mobile.deevnet.net`, and inside it
  `api.grooveiq.mobile.deevnet.net`.
- **Ownership.** The tenant authors its own records as part of its IaC. The substrate supplies DNS
  *infrastructure*, not tenant content. A tenant rebuilt from scratch must restore its own names.
- **Resolution path.** Tenants resolve through the substrate resolver; the tenant module hands
  workloads `10.20.99.1` today.

What is missing is the mechanism connecting the second point to the third.

### The problem

Two authorities that do not meet.

**The substrate's DNS is inventory-driven Ansible.** The `opnsense_dns` role reads
`env.interfaces.<name>.dns` from inventory, then writes Unbound **host overrides and aliases**
through the OPNsense API, reconciling against what is already there. That model is the exact
opposite of tenant-owned: the record's source of truth is a substrate repository, and the role has
a `dns_delete_unmanaged` mode whose whole purpose is removing records it did not put there.

**Tenants are Terraform and self-service.** A tenant that must land a commit in the substrate
inventory to publish a name is no longer self-contained, and its rebuild is no longer a tenant-only
operation. But the alternative — letting tenants write into the same Unbound configuration the
substrate reconciles — puts two authorities on one zone, where a substrate run can delete a
tenant's records and a tenant can write outside its own namespace.

Neither end of that trade is acceptable as it stands, which is why this needs a decision rather
than an implementation.

### What Proxmox offers, and why it does not fit as-is

Proxmox SDN does have DNS integration, and the EVPN zone accepts `dns`, `reversedns` and `dnszone`.
Two findings close that path in its current form:

- **Only one DNS plugin ships.** `/usr/share/perl5/PVE/Network/SDN/Dns/` contains `Plugin.pm` and
  `PowerdnsPlugin.pm` — nothing else. It wants a PowerDNS API `url` and `key`. The core router runs
  Unbound, which has no equivalent write API, so the backend would have to be something the estate
  does not run today.

- **Registration is coupled to IPAM allocation.** In `PVE/Network/SDN/Subnets.pm`, `add_dns_record`
  is called only from `add_ip` and `add_next_free_ip` — the IPAM allocation paths. The tenant module
  addresses workloads through cloud-init `ip_config` and never allocates through IPAM, which is
  verified rather than assumed: PVE's IPAM database holds **no entry** for the running tenant's
  `10.20.129.10`.

  So even with a PowerDNS backend and a shim in front of Unbound, no record would be created for a
  workload as it is provisioned today.

That second finding matters more than the first. It means a decision hides inside this one: whether
tenant addressing moves to IPAM allocation in order to inherit Proxmox's DNS hook, or whether
naming is solved independently of Proxmox and addressing stays as it is. Those pull in opposite
directions and should be settled together.

Note also that the fabric's own reason for wanting IPAM is weaker than it was: EVPN zones have no
DHCP ([ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/) as amended), so IPAM
would be adopted for naming, not for leasing.

### Constraints any answer has to satisfy

- **Tenant-owned** — authored in tenant IaC, restored by a tenant rebuild alone.
- **Substrate-resolvable** — substrate clients resolve tenant names with no per-client
  configuration.
- **Namespaced** — a tenant cannot publish into another tenant's zone or into the substrate zone.
- **Survives substrate reconciliation** — an `opnsense_dns` run must not delete tenant records.
- **Stateless substrate** — rebuilding the core router must not lose tenant names; they either
  live elsewhere or are restored from tenant IaC.
- **Reverse DNS is in scope to decide, not necessarily to deliver** — the zone option exists and
  the addressing plan is deterministic, so the record can be stated either way.

### Why this is awkward

The tension is not technical difficulty; it is that the two obvious mechanisms each violate a
settled principle. Publishing through inventory violates tenant ownership. Publishing directly into
the substrate resolver violates single-authority. Anything acceptable is likely to introduce a
*third* thing — a delegated zone, an authoritative server the fabric owns, or a namespace guard in
the reconciliation — and that is a real addition to the estate rather than a configuration choice,
which is why it belongs in a record.

---

## Decision

**A tenant publishes into its own zone, delegated from the substrate zone, served by a PowerDNS
Authoritative instance the substrate runs, and written by the tenant over RFC 2136 with a TSIG key
scoped to that zone.**

The delegation is what resolves the deadlock. Neither authority has to give ground, because they
stop sharing a zone.

### 1. Naming is solved independently of Proxmox

Tenant addressing stays as it is: cloud-init, derived from `tenant_index`. **PVE IPAM allocation is
not adopted.** The `ipam = "pve"` attribute stays on the zone because the API requires it, but
nothing allocates through it and PVE's IPAM database stays empty for tenant subnets.

This closes the fork stated in the context. Inheriting Proxmox's DNS hook would mean rewriting how
workloads are addressed in order to obtain **one A record per allocated IP**, named
`<hostname>.<dnszone>`. A tenant needs more than that — service names, aliases, several names for
one host, and records for things that are not VMs at all. It would also make Proxmox the authority
for tenant naming, re-coupling the tenant contract to a substrate implementation detail that
[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) went to some trouble to
separate.

So PowerDNS is **not** chosen because it is the only plugin PVE ships. That it is the only plugin is
now irrelevant, since the plugin is not used. It is chosen for a real zone model, RFC 2136 support,
and per-zone TSIG — the properties the constraints actually ask for.

### 2. One delegated zone pair per tenant

For tenant `t` with index `n` on site `s`:

| Zone | Pattern | mobile, `n` = 1 |
|------|---------|----------------|
| Forward | `t.s.deevnet.net` | `tdemo.mobile.deevnet.net` |
| Reverse | `{128+n}.{site_octet}.10.in-addr.arpa` | `129.20.10.in-addr.arpa` |

Both derive from the single `tenant_index` of
[ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/), so neither is a per-tenant
decision. Naming is unchanged from what this record already called settled:
`service.tenant.site.deevnet.net` still resolves, and now it resolves because something is
authoritative for `tenant.site.deevnet.net` rather than because a substrate role wrote a host
override.

Unbound on the core router gets one **domain override** per tenant zone, forwarding it to the
tenant DNS service. Substrate clients need no configuration; they ask the resolver they already ask.

Reverse DNS is delivered rather than deferred. The addressing plan is deterministic and the
delegation is already per-tenant, so the reverse zone costs one more `create-zone` at onboarding.
PTR records inside it are tenant-authored and optional.

### 3. Publication is RFC 2136 with a per-zone TSIG key

PowerDNS Authoritative has a **single, global** HTTP API key. Publishing through the API would
therefore make *Namespaced* a convention enforced by module discipline — any tenant holding the key
could write any zone. That is not what the constraint says.

Dynamic update gives the constraint teeth. Each tenant zone carries its own key:

```
pdnsutil create-zone            tdemo.mobile.deevnet.net
pdnsutil generate-tsig-key      tdemo hmac-sha256
pdnsutil set-meta               tdemo.mobile.deevnet.net TSIG-ALLOW-DNSUPDATE tdemo
pdnsutil set-meta               tdemo.mobile.deevnet.net ALLOW-DNSUPDATE-FROM 10.20.99.0/24
```

An update signed with `tdemo`'s key is accepted only for `tdemo`'s zones; anything else is REFUSED
by the server. **A tenant cannot publish outside its namespace because the server will not let it**,
not because the tenant module declines to try. That is testable, and the test belongs in the
verification for this work.

The cost is a less ergonomic Terraform provider (`hashicorp/dns` rather than a PowerDNS-native one)
and a TSIG secret per tenant in the vault. Both are accepted; the constraint was stated as a
requirement, not a preference.

### 4. The server is substrate; the zones and records are tenant

This is the same seam already drawn twice elsewhere in this estate. The core router is substrate
though every tenant packet crosses it. The tenant hypervisor is substrate though only tenant
workloads run on it. The DNS server is substrate though it holds nothing but tenant records.
**Substrate provides the machine; tenants provide the content.**

That line, not a new one, decides the tooling:

| | Owner | Provisioned by |
|---|---|---|
| PowerDNS instance and its host | Substrate | Ansible |
| Zone creation and TSIG issue | Substrate, at onboarding | Ansible |
| Unbound delegation | Substrate | Ansible |
| Records inside the zone | Tenant | The tenant's own Terraform |

No Terraform state is introduced for substrate, so
`architecture/substrate/management-plane/extended-services.md` §5 — *"Terraform is intentionally
not used for management-plane workloads"* — is honoured rather than amended.

The instance runs on **hv01**, the management hypervisor, as a container on a shared host for
substrate services that serve tenants. It does not run on hv02: a service every tenant depends on
does not belong in the tenant compute domain, and ADR-0001's plane split holds.

### 5. Onboarding is a substrate act; the tenant lifecycle is not

The constraint is *restored by a tenant rebuild alone* — not *no substrate involvement ever*.
[ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/) already
established that adding a tenant touches substrate, because egress does. Zone creation, TSIG issue
and the Unbound delegation join that same one-time step, driven from the same declared tenant list.

What must never require a substrate commit is the part that actually recurs: adding a record,
changing one, destroying and rebuilding the tenant. Those are `terraform apply` and nothing else.

---

## Consequences

**The two authorities stop meeting, so neither has to yield.** Tenant records are not in Unbound,
so `opnsense_dns` and its `dns_delete_unmanaged` mode cannot reach them — the *survives substrate
reconciliation* constraint is satisfied structurally rather than by careful configuration. This is
the property that makes the answer worth the third moving part.

**The core router becomes rebuildable without losing tenant names.** Its share of the arrangement is
one domain override per tenant, regenerated from inventory. The records themselves live in PowerDNS
and are re-derivable from tenant IaC, so *stateless substrate* holds at both ends.

**Tenant DNS availability now depends on hv01.** If hv01 is down, tenant names stop resolving —
substrate names are unaffected, because Unbound is untouched and still answers for everything it
was already authoritative for. That is the correct direction for the failure to point, and it is
better than the alternative in which the resolver itself moves. The mitigation, when it is wanted,
is a PowerDNS secondary fed by AXFR; it is deliberately not built now.

**PowerDNS shares a host with future tenant-facing services.** An OS update or a container restart
on that host takes tenant DNS with it. Accepted at lab scale, and recorded here so it is not a
surprise: it is the strongest argument for that secondary when the time comes. Substrate-facing
management services are deliberately kept off this host, on a separate one, because their change
cadence is much higher.

**This is a documented-doctrine refinement, not only an addition.**
`platforms/management-plane/management-hypervisor/_index.md` states that core network services run
on the core router, not as VMs on the management hypervisor. That still holds for substrate
*resolution*. What is new is tenant *authoritative* DNS, a class of service that did not exist when
that sentence was written. The distinction is resolution versus authority, and that document is
updated to say so.

**Seam 2 of ADR-0001 is refined.** It said tenant DNS is "published into the substrate zone". More
precisely, it is published into a zone **delegated from** the substrate zone. The ownership claim
was right; the mechanism is one level down from where it read. ADR-0001 is not rewritten.

**Adding a tenant now touches three things instead of two.** Terraform creates the fabric objects,
Ansible gives the tenant a way out (ADR-0003) and now also a zone, a key and a delegation. The
second and third are driven from one declared tenant list, so it is one Ansible run, not two. This
is the same trade ADR-0003 accepted and for the same reason: reviewable in inventory, at the cost
of a step.

**Tenants gain a real capability boundary.** A TSIG key is a credential a tenant holds, which makes
the tenant contract something a tenant is issued rather than something it is trusted to respect.
That is a better foundation for the contract work still outstanding than a shared API key would
have been.

---

## Current state

The decision is taken; the implementation is not yet built. For whoever picks it up:

- Nothing about the substrate's own DNS changes. `opnsense_dns` keeps host overrides and aliases
  exactly as it has them, and gains domain-override reconciliation for the delegations.
- No tenant name resolves yet. `tdemo-1` is still reachable by address only; the end-to-end test of
  this record is `dig tdemo-1.tdemo.mobile.deevnet.net` answered through `10.20.99.1`.
- PVE IPAM stays empty for tenant subnets, and that is now a decision rather than a gap.
- The namespace boundary must be tested, not assumed: an update signed with one tenant's key,
  aimed at another tenant's zone, must be REFUSED.
