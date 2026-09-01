---
title: "ADR-0004: Tenant DNS Publication"
weight: 4
---

# ADR-0004: Tenant DNS Publication

|  |  |
|--|--|
| **Status** | **Proposed — problem stated, not yet decided** |
| **Date** | 2026-09-01 |
| **Scope** | How a tenant's own DNS records reach the resolver substrate clients use |
| **Depends on** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/) |

---

## Context

Seam 2 of [ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) splits addressing
from naming: IPAM belongs to the fabric, while DNS is **tenant-owned but published to the substrate
zone**. With [ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/)
closing egress, this is the last part of the tenant contract still undecided.

### What is already settled

- **Naming.** A tenant's zone is `tenant.site.deevnet.net`; records are
  `service.tenant.site.deevnet.net`. So `grooveiq.dvntm.deevnet.net`, and inside it
  `api.grooveiq.dvntm.deevnet.net`.
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

**Not yet taken.** This record states the problem and the constraints; the options have not been
evaluated.

## Consequences

To be completed once a decision is made.

---

## Current state

For whoever picks this up:

- Tenant workloads resolve **through** the substrate resolver but publish **nothing**. The tenant
  module sets `dns.servers` on the workload and creates no records.
- No tenant name resolves anywhere today. `tdemo-1` is reachable by address only.
- The substrate's own DNS is complete and working; nothing here is a defect in it.
- PVE IPAM is empty for tenant subnets, so adopting Proxmox's DNS hook would mean changing how
  workloads are addressed, not just adding a backend.
