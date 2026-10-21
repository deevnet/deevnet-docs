---
title: "ADR-0040: Tenant Names Without a Site"
weight: -40
---

# ADR-0040: A Tenant's Names Do Not Name a Site

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it). Its first question, the shape of the names, is the owner's to decide |
| **Date** | 2026-10-21 |
| **Scope** | The DNS names of a tenant and its services: their shape, which names a tenant may not take, and who answers for a tenant's zone as it moves. Not reverse zones or addresses, which stay per site, and not certificates ([ADR-0039](/docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/)) |
| **Amends** | [Naming standard](/docs/standards/naming/) §5.1–§5.3, [ADR-0004](/docs/architecture/decisions/naming-and-dns/0004-tenant-dns-publication/) §2 (the forward-zone pattern), [ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §13 and the zone it publishes into; [ADR-0008](/docs/architecture/decisions/naming-and-dns/0008-host-naming-site-codes/)'s note that the tenant pattern resolves to `<tenant>.mobile.deevnet.net` |
| **Related** | [ADR-0039](/docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/) *(Proposed)*, which depends on this; [ADR-0005](/docs/architecture/decisions/naming-and-dns/0005-tenant-zone-apex-ownership/); the [Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/) |

---

## Context

**A tenant's names carry the site it was created on.** Its zone is `<tenant>.<site>.deevnet.net`
(naming standard §5.2, ADR-0004 §2), and the API builds every name from it (`Site.Zone`). A tenant
that moves to another site, or to a take-home Pi, changes every name its devices dial and every name
its certificates carry.

**A certificate's names are fixed when it is signed.** Under ADR-0039 a tenant's Service CA is
constrained to the tenant's zone for five years. A zone that changes with the site would mean a new
CA per move, which is what ADR-0039 exists to avoid.

**Tenant names are checked for shape only.** `^[a-z][a-z0-9]{0,7}$` accepts `home` and `mobile`.
The standard says tenant names "MUST be distinct from site names" (§5.1), but nothing enforces it,
and there is no list of reserved labels.

**`deevnet.net` is internal.** Each site's resolver answers its site zone and forwards each tenant
zone to the tenant DNS server; nothing is delegated in public DNS, and nothing is meant to be.

## Decision

### 1. A tenant's zone names the tenant and nothing else

**A tenant's zone stays the same wherever the tenant lives**, and its services are `<service>.` in
it. Which zone that is has two candidates, and this record leaves the choice to the owner:

| Option | |
|---|---|
| **A. Directly under the apex: `<tenant>.deevnet.net`** *(the owner's preference)* | The shortest names, and what the owner has proposed. Tenant zones sit beside site zones (`mobile`, `home`), the Builder (`dv00bld001p01.deevnet.net`) and apex aliases (§4.3). A CA can exclude the names known when it is signed, but not those added later (ADR-0039 §4) |
| B. Under a tenant subtree: `<tenant>.t.deevnet.net` *(the review's leaning)* | One label longer. The Tenants CA permits only the subtree, a bound that does not age: no site, host or alias ever falls inside it, and none needs excluding. It matters because the Tenants CA is an online key on a kit that travels |

**Either way, a tenant's name is fixed at creation.** Renaming a tenant is a new tenant.

### 2. Some labels are reserved, and the API refuses them

**A tenant may not take a label that names a site, a site code, a retired zone, or a service alias
at the apex**: `home`, `mobile`, `mgmt`, `dvnt`, `dvntm`, and every label in naming standard §4.3's
alias list, now and as it grows. The API's name check enforces the list, in place of the standard's
§5.1 sentence alone. Under option B the list is short, since only the subtree's own label is
contested.

### 3. A tenant's zone is answered where the tenant lives

**The site that hosts a tenant answers for its zone**: its tenant DNS server holds the zone, and its
resolver forwards it, as today. A tenant that moves has its zone created at the new site and removed
from the old one. Nothing is delegated publicly. A take-home Pi's names are its owner's to answer
(ADR-0041); the devices there verify a name without having to resolve it.

**Two sites may answer the same tenant zone**, each in its own resolver, if a tenant runs at both.
There is no path between sites, so nothing reconciles them; each answers for what it hosts.

### 4. What stays per site

**Reverse zones, addresses and a tenant's index stay per site** (ADR-0015 §1 and §8): a tenant that
moves gets a free index at the new site, and its reverse zone with it. Only forward names leave the
site.

---

## Consequences

**Every tenant name changes once.** `<service>.<tenant>.mobile.deevnet.net` becomes the new shape,
in DNS, in the API (`Site.Zone`), in the provider and in each tenant's code. The old names can be
kept as aliases for a period, chosen when this is built.

**A tenant DNS server holds zones that are not under its site's zone**, and the resolver forwards
them. Its apex NS still names a host in the site's zone (ADR-0005).

**Tenant names become a shared namespace across sites**: a name taken at one site is taken
everywhere, because the zone is the same. Today the factory is the only site that creates tenants.

---

## Alternatives considered

- **Rejected: keep the site in the name, and constrain a tenant's CA to every zone it may use.**
  Each new site the tenant moves to means a new CA and new device anchors.
- **Rejected: a public delegation of `deevnet.net`.** Tenant names are internal on purpose.

---

## Open questions

1. **Option A or B** (§1): the owner's decision.
2. **How long do the old site-scoped names live on as aliases?**
3. **If a second site ever creates tenants**, how is a name kept unique? (ADR-0039's third open
   question.)

---

## What would settle it

1. **The resolver forwards a tenant zone outside the site zone** and answers it; a name that is
   in no zone falls through as it does today.
2. **The API refuses every reserved label**, and builds every name from the new zone.
3. **Under option B**, Go and OpenSSL refuse a certificate from a CA constrained to the subtree for
   any name outside it.
