---
title: "ADR-0040: Tenant Names Without a Site"
weight: -40
---

# ADR-0040: A Tenant Has Canonical Names Under `t.deevnet.net`, and May Have Vanity Names Under `deevnet.net`

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it) and the [decision register](/docs/architecture/reviews/2026-10-tenant-pki/#decision-register) |
| **Date** | 2026-10-21 |
| **Revised** | 2026-10-21, before review: the owner chose the tenant subtree for canonical names and asked for vanity names under `deevnet.net`. The apex-only option is now an alternative considered |
| **Scope** | A tenant's DNS names: canonical names for services and devices, optional vanity names for people, which names a tenant may not take, what certificate each kind of name needs and who may issue it, and how names follow a tenant that moves. Not reverse zones or addresses, which stay per site |
| **Amends** | [Naming standard](/docs/standards/naming/) §5.1–§5.3; [ADR-0004](/docs/architecture/decisions/naming-and-dns/0004-tenant-dns-publication/) §2 (the forward-zone pattern); [ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §13 (the zone it publishes into); [ADR-0008](/docs/architecture/decisions/naming-and-dns/0008-host-naming-site-codes/)'s note that the tenant pattern resolves to `<tenant>.mobile.deevnet.net`; [ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/) §3 (the zone a tenant certificate names) |
| **Related** | [ADR-0039](/docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/) *(Proposed)*, which depends on this; [ADR-0005](/docs/architecture/decisions/naming-and-dns/0005-tenant-zone-apex-ownership/); [ADR-0036](/docs/architecture/decisions/platform-services/0036-service-proxy/); the [Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/) |

---

## Context

**A tenant's names carry the site it was created on.** Its zone is `<tenant>.<site>.deevnet.net`
(naming standard §5.2, ADR-0004 §2), and the API builds every name from it. A tenant that moves
changes every name its devices dial and every name its certificates carry.

**A CA's name constraints are fixed when it is signed**, and nothing can be issued below a CA for a
name outside its constraints. ADR-0039 constrains a tenant's Service CA to the tenant's zone for
five years, and the Tenants CA to all tenant zones for ten.

**Names directly under `deevnet.net` are crowded.** Site zones (`mobile`, `home`), the Builder
(`dv00bld001p01.deevnet.net`) and the apex aliases of naming §4.3 live there, with more to come. A
CA can exclude only the names known when it is signed.

**Tenant names are checked for shape only.** `^[a-z][a-z0-9]{0,7}$` accepts `home`, `mobile` and
`t`. There is no reserved list.

**People and devices want different names.** A person types `console.eds.deevnet.net`. A device is
better served by a name in a namespace no CA outside the tenant can issue for.

**`deevnet.net` is internal.** Each site's resolver answers its site zone and forwards each tenant
zone to the tenant DNS server; nothing is published publicly.

## Decision

### 1. Canonical names are under `t.deevnet.net`

**A tenant's canonical zone is `<tenant>.t.deevnet.net`**, its services are
`<service>.<tenant>.t.deevnet.net`, and they do not change for the tenant's life. For EdS:
`mqtt.eds.t.deevnet.net`, `console.eds.t.deevnet.net`.

**Canonical names are what machines use**, and what the tenant's Service CA issues for. The Tenants
CA permits `t.deevnet.net` only (ADR-0039 §3). Under RFC 5280 that covers `t.deevnet.net` and
everything below it, and nothing else, now or later.

### 2. Vanity names are under `deevnet.net`, for people, and optional

**A tenant may have vanity names `<label>.<tenant>.deevnet.net`**: `console.eds.deevnet.net`. They
are for browsers and people. Devices do not use them.

**A vanity name resolves by CNAME to its canonical name**:
`console.eds.deevnet.net. CNAME console.eds.t.deevnet.net.`

**DNS does not satisfy TLS.** A browser that asks for `console.eds.deevnet.net` checks the
certificate for `console.eds.deevnet.net`, whatever the CNAME says. So a vanity name needs a
certificate that names it, and the tenant's Service CA cannot issue one (its constraint is the
canonical subtree).

**Who may issue for a vanity name**, the one new authority this record needs:

| Option | |
|---|---|
| **A. A Deevnet Names CA** *(leaning)* | Signed by the root (`pathlen:0`, leaves only), its key in the factory's PKI secret store with the Tenants CA (ADR-0042). The API issues a vanity certificate only to the tenant whose label is the vanity name's second label, only for `<label>.<tenant>.deevnet.net`, never a wildcard. It permits `deevnet.net` and excludes `t.deevnet.net` and the site zones known at signing. The certificate travels with the tenant, as canonical ones do. It is an online issuer for most of `deevnet.net`: stolen, it can impersonate an unexcluded name to any client that anchors at the root, as the Tenant Service CA can today. Devices never trust it |
| B. A public CA, through DNS-01 | Trusted everywhere, with no new private authority. It needs `deevnet.net` published publicly for the challenge and the internet at every issuance, with lifetimes shrinking to 47 days by 2029 (ADR-0031). That conflicts with an autonomous factory, though the application itself never has to be reachable |
| C. A site ingress, with the site's certificate | A vanity name is answered by the hosting site's proxy (ADR-0036) and certified by that site. Portable only by reissuing at every site, and a take-home Pi has no site |

**Where TLS for a vanity name ends: at the tenant's own endpoint, by SNI.** Its server presents the
vanity certificate to a client that asks for the vanity name, and the canonical one otherwise. A
site ingress may be added later; it is not required.

**A vanity name grants nothing the canonical one does not.** It names the same service. The Names CA
issues it under the same ownership rule, and devices never anchor at the Names CA. So a vanity name
cannot carry a tenant past its canonical namespace.

**The CA's name need not mirror DNS.** CAs are named for what they are (`Deevnet Names CA`); only a
certificate's SANs must match the name a client dialed.

### 3. Some labels are reserved, and the API refuses them

**A tenant may not take a label that is a site, a site code, a retired zone, `t`, or an apex alias**:
`home`, `mobile`, `mgmt`, `dvnt`, `dvntm`, `t`, and every label in naming §4.3's alias list, now and as
it grows. The API's name check enforces it, in place of §5.1's sentence alone. A tenant name owns
both its canonical zone and its vanity space, so the same list guards both.

### 4. Names are answered where the tenant lives

**The site that hosts a tenant answers both its zones**: `<tenant>.t.deevnet.net` and, if it has
vanity names, `<tenant>.deevnet.net`. Its tenant DNS server holds them, and its resolver forwards
them, as today. A tenant that moves has its zones created at the new site and removed from the
old. Certificates do not change.

**A take-home Pi's names are its owner's to answer.** Its devices verify a name without resolving it
(ADR-0041 §2).

**Two sites may answer the same tenant's zones** if it runs at both. There is no path between sites,
and each answers for what it hosts.

**There is one view, internal.** No public DNS view is needed unless option B is chosen.

### 5. What stays per site

**Reverse zones, addresses and a tenant's index stay per site** (ADR-0015 §1, §8). Only forward
names leave the site.

---

## Consequences

**Every tenant name changes once**: `<service>.<tenant>.mobile.deevnet.net` becomes
`<service>.<tenant>.t.deevnet.net`, in DNS, in the API (`Site.Zone`), in the provider and in each
tenant's code. The old names can be kept as CNAMEs for a period.

**Two zones per tenant with vanity names**, both forwarded by the resolver.

**A new online issuer, the Names CA**, if option A is chosen. Its scope is broad, and its control is
the API's ownership rule.

**Tenant names become one namespace**: a name taken is taken everywhere.

---

## Alternatives considered

- **Rejected (owner's decision, 2026-10-21): canonical names directly under the apex,
  `<tenant>.deevnet.net`.** Shortest. But no constraint on the Tenants CA can keep up with names
  added under `deevnet.net` later. It survives as the vanity namespace, which machines do not trust.
- **Rejected: keep the site in the name, and constrain a tenant's CA to each zone it uses.** Every
  move is a new CA and new device anchors.
- **Rejected: a CNAME alone for vanity names.** TLS checks the name dialed.
- **Rejected: wildcard vanity certificates.** One key would answer for every label in a tenant's
  vanity space, and ADR-0037 already refuses wildcards.

---

## Open questions

1. **Vanity issuer: option A, B or C** (§2).
2. **How long do the old site-scoped names live on as CNAMEs?**
3. **If a second site ever creates tenants, how is a name kept unique?**

---

## What would settle it

V2, V4 and V10 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan).
