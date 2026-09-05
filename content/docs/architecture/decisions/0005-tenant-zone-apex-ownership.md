---
title: "ADR-0005: Tenant Zone Apex Ownership"
weight: 5
---

# ADR-0005: Tenant Zone Apex Ownership

|  |  |
|--|--|
| **Status** | Accepted |
| **Date** | 2026-09-03 |
| **Scope** | Who owns the SOA and apex NS records inside a delegated tenant zone |
| **Extends** | [ADR-0004: Tenant DNS Publication](/docs/architecture/decisions/0004-tenant-dns-publication/) |

---

## Context

[ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) drew a clean line: the
substrate creates the zone and issues the TSIG key, and the tenant writes the records inside it.
*Substrate provides the machine; tenants provide the content.*

Building it exposed a category the line does not cover. A zone's **apex** — its SOA, and the NS
records naming the servers authoritative for it — is made of records, which puts it on the tenant
side of that table. But it is created by `pdnsutil create-zone`, which is a substrate act, and it
describes the zone's own existence rather than anything the tenant runs. It is neither the machine
nor the content.

Leaving the question unanswered has a default, and the default is wrong. The first live deployment
produced this:

```
$ dig @10.20.99.30 tdemo.mobile.deevnet.net SOA +short
a.misconfigured.dns.server.invalid. hostmaster.tdemo.mobile.deevnet.net. 0 10800 3600 604800 3600

$ dig @10.20.99.30 tdemo.mobile.deevnet.net NS +short
(nothing)
```

`a.misconfigured.dns.server.invalid.` is PowerDNS's literal placeholder for an unset
`default-soa-name`. The zone also has no apex NS at all, because `pdnsutil create-zone` with no
further arguments creates an empty zone and PowerDNS does not invent one.

### Why this is not cosmetic

**A zone with no apex NS is malformed.** It resolves today only because the substrate side of
[ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) is an Unbound **domain
override** — a forward, not a referral. Forwarding never consults the child's NS set, so the defect
is invisible. Any move toward real delegation, any resolver that validates the child against the
parent, and any second server added later will meet a zone that cannot say who serves it.

**The SOA is load-bearing for the future secondary.** ADR-0004 names an AXFR-fed PowerDNS secondary
as the mitigation for tenant DNS depending on hv01. The SOA MNAME and its serial are what a
secondary uses to find its primary and decide whether to transfer. A placeholder primary in an
invalid TLD is precisely the wrong thing to discover at the point of building that.

**It is a per-zone defect, so it multiplies.** Every tenant onboarded before this is answered
inherits it, and fixing it later means rewriting apexes under live TSIG keys rather than setting
them once at creation.

### The question this actually asks

Not "what should the SOA say" — that is configuration. The decision is **which side of the tenant
contract the apex belongs to**, because that determines who sets it, when, and what happens to it on
a tenant rebuild.

---

## Options considered

**1. The tenant owns its apex.** It is made of records, and the tenant's TSIG key can already write
them, so no mechanism is needed. But a tenant's `terraform destroy` would strip the zone's own NS
and SOA and leave a broken zone behind for the substrate to find — the tenant would be able to
delete the zone's identity without deleting the zone. It also makes every tenant restate
infrastructure it did not choose and cannot see: the name of the substrate's DNS host is not tenant
knowledge.

**2. The substrate owns the apex, set at zone creation.** The apex describes the zone, and the
substrate creates zones. A tenant rebuild then restores tenant names against a zone whose identity
never went away, which is what *stateless substrate* asks for. Costs a `default-soa-name` in
`pdns.conf` and an explicit apex NS at onboarding.

**3. Leave it unset.** Zero work, and forwarding hides it indefinitely. Rejected: it is a latent
defect in every zone, it blocks the secondary that ADR-0004 already names as the availability
mitigation, and "it works because nothing checks" is not a property to build on.

---

## Decision

**The zone apex — SOA and apex NS — is substrate-owned, set when the zone is created, alongside the
TSIG key.**

This extends [ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) §4 rather than
altering it. That table gains a row, and the principle it states is unchanged: the apex is part of
the machine, not the content.

| | Owner | Provisioned by |
|---|---|---|
| PowerDNS instance and its host | Substrate | Ansible |
| Zone creation and TSIG issue | Substrate, at onboarding | Ansible |
| **Zone apex — SOA and apex NS** | **Substrate, at onboarding** | **Ansible** |
| Unbound delegation | Substrate | Ansible |
| Records inside the zone | Tenant | The tenant's own Terraform |

### The apex NS target must be a name with an address record

RFC 2181 §10.3 forbids an NS record pointing at an alias. The `tdns` name provisioned for the DNS
host today is an Unbound **host alias**, which resolves as a CNAME, so it cannot be the apex NS
target. The apex NS therefore names the host's own A record —
`tenant-mgmt-vm01.mobile.deevnet.net` — and `tdns` remains what it is: a convenience name for
operators and for the `dns_update_server` variable, neither of which is a delegation.

The same applies to the SOA MNAME, which should name the primary rather than a placeholder.

### Reverse zones are treated identically

The reverse zone is created by the same onboarding step and has the same apex problem. Nothing about
this decision is specific to the forward zone.

### Existing zones are corrected, not grandfathered

`tdemo`'s zones already carry the placeholder apex. The provisioning step reconciles the apex on
every run rather than only at creation, so the fix reaches zones that already exist. This is the one
place where the substrate writes into a live tenant zone after onboarding, and it is confined to the
apex.

---

## Consequences

**This boundary is a convention, not a control — unlike the one it extends.** That asymmetry is the
most important thing in this record. ADR-0004's namespace boundary has teeth: a tenant's key is
refused by the server for another tenant's zone, so *Namespaced* is enforced rather than trusted.
The apex boundary has no such backing. `TSIG-ALLOW-DNSUPDATE` is granted per **zone**, PowerDNS has
no per-RRset ACL, and a tenant's own key can therefore rewrite its own SOA and apex NS. The
substrate sets the apex and reconciles it; it cannot prevent a tenant from changing it in between.

Stating that plainly is the point. It would be easy to read the table above and assume the apex is
protected the way the namespace is. It is not, and anyone reasoning about the tenant contract needs
to know which of its lines are enforced and which are agreements. If it ever needs teeth, PowerDNS
offers no per-RRset ACL and the answer would be a Lua update policy — deliberately not built now,
at lab scale, for a boundary no tenant has an incentive to cross.

**The tenant contract gains an obligation the tenant cannot see.** A tenant must not write its own
apex, but nothing in its Terraform tells it so, and nothing stops it. This belongs in the tenant
contract documentation rather than only here.

**Reconciling the apex means the substrate writes into live tenant zones.** ADR-0004 was able to say
that after onboarding, the recurring operations are `terraform apply` and nothing else. That is now
true with an exception: an Ansible run may correct the apex of a zone that already has records in
it. The blast radius is one RRset pair per zone and the operation is idempotent, but the clean claim
is gone and this is where it went.

**The future secondary becomes buildable.** With a real SOA MNAME and an apex NS naming the primary,
the AXFR-fed secondary in ADR-0004's consequences is a configuration change rather than a
correction of every existing zone. That was the strongest practical reason to decide this now rather
than when the secondary is wanted.

**Zone creation is no longer a single command.** Onboarding gains apex reconciliation next to
`create-zone`, `generate-tsig-key` and the two `set-meta` calls. It stays one Ansible run driven from
the same declared tenant list, so the cost lands in role complexity rather than in operator steps.

---

## Current state

- `tdemo.mobile.deevnet.net` and `129.20.10.in-addr.arpa` exist on `10.20.99.30` with the placeholder
  apex described above. Both answer; neither has an NS.
- The Unbound delegation is not yet in place, so nothing resolves tenant names through
  `10.20.99.1` yet and the malformed apex is not currently reachable by any client.
- No tenant has written a record yet, so correcting the apex touches nothing a tenant owns.
