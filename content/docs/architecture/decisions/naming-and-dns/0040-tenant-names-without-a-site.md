---
title: "ADR-0040: Tenant Names Without a Site"
weight: -40
---

# ADR-0040: A Tenant Service Is Named `<service>.<tenant>.deevnet.net`, and Its Sites Are Extra Names

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it) and the [decision register](/docs/architecture/reviews/2026-10-tenant-pki/#decision-register) |
| **Date** | 2026-10-21 |
| **Revised** | 2026-10-21, before review, and 2026-10-25 in the [Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/). The drafts of 2026-10-21 put canonical names under `t.deevnet.net` and made vanity names optional, for people only, issued by a Names CA. All three are withdrawn: the site-less name is the service's identity, and the tenant CA issues it. 2026-10-26: site-less names resolve only at production sites (§1), so the Mobile Factory answers a tenant by its site names alone |
| **Scope** | A tenant's DNS names: the name that identifies each service, the per-site names beside it, what a tenant certificate carries, which labels a tenant may not take, the bus name devices dial, and how names follow a tenant between sites. Not reverse zones or addresses, which stay per site |
| **Amends** | [Naming standard](/docs/standards/naming/) §5.1–§5.3; [ADR-0004](/docs/architecture/decisions/naming-and-dns/0004-tenant-dns-publication/) §2 (a tenant has a site-less zone beside its site zone); [ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §13 (the names it publishes); [ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/) §3 (the names a tenant certificate carries, and the secret store's signing role) |
| **Related** | [ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/) *(Proposed)*, which depends on this; [ADR-0005](/docs/architecture/decisions/naming-and-dns/0005-tenant-zone-apex-ownership/); [ADR-0008](/docs/architecture/decisions/naming-and-dns/0008-host-naming-site-codes/); [ADR-0036](/docs/architecture/decisions/platform-services/0036-service-proxy/) |

---

## Context

**A tenant's names carry the site it runs on.** Its zone is `<tenant>.<site>.deevnet.net` (naming
standard §5.2, ADR-0004 §2), and the API builds every name from it (ADR-0037 §3). A tenant developed
on the Mobile Factory and deployed elsewhere changes every name its devices dial and every name its
certificates carry.

**TLS checks the name a client dialed against the certificate's SANs.** A CNAME does not change
that, and the CN is ignored when SANs are present (RFC 6125).

**The tenant CAs can issue any name under `deevnet.net`** (ADR-0039 §2), so a site-less name needs no
new CA.

**Tenant names are checked for shape only.** `^[a-z][a-z0-9]{0,7}$` accepts `home`, `mobile` and
`mqtt`. There is no reserved list.

**`deevnet.net` is internal.** Each site's resolver answers its site zone and forwards each tenant
zone to the tenant DNS server; nothing is published publicly.

## Decision

### 1. A service's identity is its site-less name

**Every tenant service is named `<service>.<tenant>.deevnet.net`**, for its whole life, wherever it
runs: `console.eds.deevnet.net`, `mqtt.eds.deevnet.net`. People and devices both dial it. It is
the passport of a service, as a device's URI is of a device (ADR-0039 §4).

**Site-less names resolve only at the sites where a tenant runs in production.** Such a site
answers `<tenant>.deevnet.net` with its own deployment. **The Mobile Factory does not:** it builds
tenants, and names a tenant there only under its site zone, `<tenant>.mobile.deevnet.net`. A tenant
built at the factory is reached and tried there by its site names, and takes its site-less names
to the site it is deployed to. The factory never answers for a tenant's production names, so no
site's DNS shadows another's.

**The certificate carries both regardless** (§3): the names a certificate holds do not depend on
where they resolve, so moving a tenant from the factory to production needs no reissue.

### 2. A site name is an extra name for one deployment

**A tenant service also has `<service>.<tenant>.<site>.deevnet.net` at each site it runs on or is
headed for**: `console.eds.mobile.deevnet.net`, `console.eds.home.deevnet.net`. A site name reaches
one deployment in particular, for instance dev beside prod. At the Mobile Factory it is the only
name that resolves (§1).

### 3. A tenant certificate names the service, then its sites

**The CN and the first SAN are the site-less name; the site names follow as SANs.**

```
CN:   console.eds.deevnet.net
SANs: console.eds.deevnet.net
      console.eds.mobile.deevnet.net
      console.eds.home.deevnet.net
```

**The API builds every name from a label and the tenant's sites.** A tenant sends labels, never
names, as in ADR-0037 §3. The sites come from the tenant's record: the site it runs on and any it
is headed for. A move to a site already listed needs no new certificate. A move to a new one is a
reissue, in a work session.

**No wildcard, no address, no name outside the tenant's own**, as in ADR-0037 §3.

**The signing role can no longer hold the line on its own.** ADR-0037 §3's role permits names at
least two labels below a site zone. A site-less name, `console.eds.deevnet.net`, is two labels below
`deevnet.net`, and so is a site's substrate name, `grafana.mobile.deevnet.net`. What tells them apart
is the second label, a tenant or a site. The reserved list (§4) is what keeps them apart, so the
signing role must enforce it too. How (a role per tenant, written at creation, or a check
OpenBao's roles can express) is an [open question](#open-questions).

### 4. Some labels are reserved, and the API refuses them

**A tenant may not take a label that is a site, a site code, a retired zone, a global alias, or
`device`**: `home`, `mobile`, `mgmt`, `dvnt`, `dvntm`, `device`, every global alias under naming
§4.3 (`artifacts` among them), and the bus name (§5), now and as the list grows. A tenant named
`artifacts` would own `artifacts.deevnet.net`, the alias, and a tenant named `mobile` would own the
site's substrate names.

**A service label may not be `device`**, which holds a tenant's device CNs (ADR-0039 §4).

**The API's name check enforces the list**, in place of §5.1's sentence alone. Tenant names are one
namespace: only the Mobile Factory creates tenants (ADR-0039), so a name taken is taken everywhere.

### 5. Devices dial one bus name at every site

**The broker is reached at `mqtt.deevnet.net`**, a global alias under naming §4.3 that each site
answers with its own broker. **Each site's broker certificate carries it as a SAN**, issued by that
site's Substrate CA, beside the broker's site name. A device dials the same name at every site.

**Only a site broker's certificate may carry the bus name.** The API refuses it as a tenant label
and as a SAN, and no take-home Pi's certificate carries it, so a stolen Pi key cannot answer for the
bus.

### 6. What stays per site

**Reverse zones, addresses and a tenant's index stay per site** (ADR-0015 §1, §8). Only forward names
leave the site.

---

## Consequences

**A tenant in production gains a second zone, `<tenant>.deevnet.net`**, answered by the production
site that hosts it. The Mobile Factory creates no site-less zone (§1).

**Firmware at a production site dials site-less names** for the tenant's own services,
`<service>.<tenant>.deevnet.net`. At the Mobile Factory it dials site names, so a device that is
moved between the two holds what each site needs.

**Existing tenants are reissued once**, their certificates gaining the site-less name. Their site
names stay valid, so nothing breaks while firmware moves to site-less names.

**The reserved list becomes load-bearing**, for both the API and the signing role.

---

## Alternatives considered

- **Withdrawn: canonical names under `t.deevnet.net`** (2026-10-21). A subtree gave a Tenants CA a
  name constraint that did not age. There is no Tenants CA (ADR-0039), and mbedTLS enforces no
  constraint anyway.
- **Withdrawn: vanity names for people only, from a Names CA.** A second issuer for a name the tenant
  CA can issue, and devices kept off the name that never changes.
- **Rejected: a CNAME alone for the site-less name.** TLS checks the name dialed.
- **Rejected: keep the site in the only name.** Every move would change what devices dial.
- **Rejected: wildcard certificates.** ADR-0037 already refuses them.

---

## Open questions

1. **How the signing role enforces the reserved list** (§3): a role per tenant, written by the API
   at creation, or a constraint OpenBao's roles can express. A role the API writes needs a policy
   that lets it write roles, which a faulty API could abuse.
2. **Whether the Mobile Factory answers the bus name** (§5). `mqtt.deevnet.net` is the platform's
   alias, not a tenant's, so §1's production-only rule does not decide it.

---

## What would settle it

V2, V4 and V10 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan).
