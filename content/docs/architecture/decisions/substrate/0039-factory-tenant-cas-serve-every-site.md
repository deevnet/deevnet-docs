---
title: "ADR-0039: The Mobile Factory's Tenant CAs Serve Every Site"
weight: -39
aliases:
  - /docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/
---

# ADR-0039: The Mobile Factory's Tenant CAs Serve Tenants at Every Site, and Each Site Keeps Only Its Own Substrate CAs

|  |  |
|--|--|
| **Status** | Proposed. Built in part, as of 2026-10-31: §2, the tenant CAs re-keyed under the Mobile Site CA ([CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)); §3, devices holding only the Deevnet Root, shown by three ESP32s ([CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/)). §4 and §5 wait on [CHG-0034](/docs/changes/2026/0034-device-certificates/); see [What would settle it](#what-would-settle-it) and the [decision register](/docs/architecture/reviews/2026-10-tenant-pki/#decision-register) |
| **Date** | 2026-10-20 |
| **Revised** | 2026-10-21, twice, and 2026-10-25, in the [Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/). The drafts of 2026-10-21 put a Tenants CA beside the Site CAs, gave each tenant its own Service and Device CA, had devices anchor at their tenant's Service CA, and routed a shared broker by SNI to a listener per tenant. All of that is withdrawn (see [Alternatives considered](#alternatives-considered)). The hierarchy stays as ADR-0031 built it |
| **Scope** | Which CAs a site has, which CA issues a tenant's certificates wherever the tenant runs, what a device trusts, what identifies a device, and what changes when a tenant or a device moves between sites. Not names ([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/)), not a take-home Pi ([ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/)), not the secret store ([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/)) |
| **Extends** | [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/): another site's CAs, and the scope of the mobile site's tenant CAs |
| **Amends** | ADR-0031 §3 (the tenant CAs are the Mobile Factory's, not one pair per site) and §5 (the device URI and CN drop the site); [ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/) §1 (no Tenant Service CA per site) and §6 (the broker's checks); the [Certificates standard](/docs/standards/certificates/) §1 tables, once accepted |
| **Depends on** | [ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) *(Proposed)* for the names a tenant certificate carries; [ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/) *(Proposed)* for where the tenant CA keys are held |
| **Related** | [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) §4, [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §8 and §10, [ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/) §2, [ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/), [CHG-0034](/docs/changes/2026/0034-device-certificates/), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) |

---

## Context

**The mobile site is the Deevnet IoTaaS Mobile Development Factory**, the Mobile Factory for short.
It is a contractor site: it
creates every tenant, develops with it, and does the tenant's certificate work, either on site where
the tenant's devices are or with the devices brought to the kit. It travels, often with no upstream,
and depends on no other site. **Only the Mobile Factory creates tenants.** Another site that ever does would
need decisions of its own.

**A tenant is developed on the Mobile Factory and usually deployed at another site.** Its devices go
with it.

**The PKI is ADR-0031's, as built.** The Deevnet Root CA (offline, `pathlen:2`) signs one Site CA
per site (offline, `pathlen:1`, permitting `deevnet.net` and private addresses). The mobile Site CA
signs three issuing CAs: the Substrate CA (its key in the site's vault, issued by Ansible), the Tenant
Device CA and the Tenant Service CA (ADR-0037), both inside OpenBao. **The two tenant CAs carry no
name constraints of their own**, so they can issue for any name under `deevnet.net`.

**What constrains any answer:**
- **mbedTLS, on most tenant devices, enforces no name constraints** (ADR-0031 §2).
- **There is no revocation** (ADR-0031).
- **The broker is the platform's, not a tenant's.** Devices and tenant workloads both dial out to it
  and meet there (ADR-0012).

## Decision

### 1. Each site has only its own substrate's CAs

**A site has a Site CA and a Substrate CA, and nothing for tenants.** Another site's are made as the
mobile site's were:
- **its Site CA**: signed by the root in a ceremony (the ceremony tools' path 2, "a Site CA only"),
  held offline, ten years, the same name constraints;
- **its Substrate CA**: its key generated on the control node and kept in that site's vault, its
  request signed by the Site CA (path 3), five years;
- **its infrastructure certificates**, its core router's among them: issued by Ansible on the
  control node from its Substrate CA.

**The substrate never depends on the Mobile Factory or on OpenBao for a certificate** (ADR-0031 §4).
A site's infrastructure is built and renewed at that site.

### 2. The Mobile Factory's tenant CAs issue for every site

**The Tenant Service CA and the Tenant Device CA under the mobile Site CA are the Mobile Factory's**,
and they issue for every tenant wherever it runs. A certificate for a service at the home site chains
`leaf → Tenant Service CA → Mobile Site CA → Deevnet Root`, and the Site CA's `deevnet.net`
constraint permits every name in `home.deevnet.net`. Their keys were made inside OpenBao and cannot
leave it, so ADR-0042 §4 replaces each once, outside it. The new CAs are signed by the Mobile Site
CA under names without a site, `Deevnet Tenant Service CA` and `Deevnet Tenant Device CA`. They stay
children of the Mobile Site CA because the mobile site is the Mobile Factory, and the factory is
what *mobile* means here. A CA's name is a label, not a scope.

```
Deevnet Root CA                     offline · the one anchor for people, computers and devices
├── Deevnet Mobile Site CA          offline · the Mobile Factory
│   ├── Deevnet Mobile Substrate CA     the factory's own infrastructure      key: vault, used by Ansible
│   ├── Deevnet Tenant Service CA       tenant servers, at every site         key: vault → imported into OpenBao
│   └── Deevnet Tenant Device CA        tenant devices, at every site         key: vault → imported into OpenBao
└── Deevnet <Site> Site CA          offline · any other site
    └── Deevnet <Site> Substrate CA     that site's own infrastructure        key: that site's vault, used by Ansible
```

**A new site costs two CAs, its Site CA and its Substrate CA.** Both are for its own
infrastructure, which needs them whether or not it hosts a tenant.

**Tenant certificates are issued only while the Mobile Factory's OpenBao is open for a work session**
(ADR-0042), when a tenant is created, a certificate renewed, or a device enrolled. What authorizes
an issuance is the tenant's API token, never the request (ADR-0037 §2). A request and a certificate
are public, so they may travel to the Mobile Factory by any medium.

### 3. A device trusts the Deevnet Root

**Every client trusts the Deevnet Root CA, and only it**, devices included. Certificates standard
1.3 stands unchanged. A device accepts a site's broker, a tenant's service and a Deevnet take-home
Pi alike, at any site, and a device moved between sites takes no new anchor.

**What that costs on mbedTLS:** a device enforces no name constraints, so it would accept a
certificate for its broker's name from any CA under the root. Only the holders of the issuing CA
keys can make one: Ansible (Substrate CAs) and the Mobile Factory in a work session (tenant CAs).

### 4. A device's identity carries no site

**A device certificate is its passport.** The Tenant Device CA issues it once. Its URI is
`urn:deevnet:tenant:<tenant>:device:<device>` and its CN `<device>.device.<tenant>.deevnet.net`,
both set by the API from the device's registration, never from the request. Neither names a site,
so a device that moves keeps its certificate.

**The CN sits under a reserved `device` label** in the tenant's space, so that no device can be
given a name that a tenant service holds (ADR-0040 §3).

### 5. A device is admitted by a site's registration, its certificate and its key

**Registration at a site is the device's visa.** A site's broker admits a device only if:
1. **its certificate chains to the Tenant Device CA** (authentication);
2. **its URI names a device registered at that site** and not removed (authorization; its grants are
   that device's topics, ADR-0012 §10);
3. **its public key matches the fingerprint recorded when its certificate was issued.**

**The fingerprint check is what makes a stolen Tenant Device CA key not enough.** Without it, the key
could mint a certificate for any registered device's URI, and deregistering would refuse only the
genuine device. With it, a forged certificate carries a key that no registration records.

**Every site's broker accepts the Tenant Device CA.** A device brought back to the kit for
maintenance connects as it is, and a device deployed at another site needs a registration there,
not a new certificate. Deregistering a device is how it is refused, in place of revocation.

### 6. A planned move changes no certificate

**Identity is site-less, so a move to a site the tenant was headed for changes only DNS and
registration.**

| What moves | What changes |
|---|---|
| A tenant service | Nothing, if the site is already in its certificate's SANs (ADR-0040 §3). A site not yet listed is added by a reissue, in a work session. Its site-less name, and so what devices dial, never changes |
| A device | A registration at the new site. Its certificate and its anchor stay |
| Anything | Nothing a client trusts |

### 7. The site-level tenant CA plan is withdrawn

**ADR-0031 §3 and ADR-0037 §1 planned a pair of tenant CAs per site.** Another site gets none, and
the mobile site's pair serves every site. It is re-keyed once (ADR-0042 §4), and what the current
keys issued runs to expiry: `eds`'s console certificate and CHG-0047's probe certificates. The
Tenant Device CA has issued nothing.

### 8. At another site, a tenant is a Deevnet Pi

**A tenant deployed at another site runs on its Deevnet Pi**, which carries its broker, log store and
dashboards (ADR-0041). **The Pi is its devices' broker and registry**: its devices' registrations and
key fingerprints are written at the Mobile Factory when it is provisioned, and its broker applies §5's
checks.

**The site gives the Pi a network and names, nothing else.** Its VLANs, firewall and Wi-Fi, and DNS for
the Pi's names (ADR-0040), come from that site's inventory, applied by Ansible from the Builder on a
visit. The site runs no broker, registry or Deevnet API for tenants.

**A tenant at another site has no self-service.** A change starts at the Mobile Factory and arrives as
a new image or a configuration change.

---

## Consequences

**The hierarchy built in CHG-0033 and CHG-0047 is the target.** Another site adds its own two CAs,
and the tenant CAs serve every site.

**One compromise of a tenant CA reaches tenants at every site.** That was already so for devices:
none enforces a per-site boundary on mbedTLS. With no revocation, a forged server certificate stays
usable until the issuing CA expires, up to five years. That is accepted
([risk R-14](/docs/policies/risk-management/risk-register/)).

**The broker gains two checks**: a device registered at this site, and a key that matches its
recorded fingerprint. The registry records a fingerprint at each issuance.

**The Mobile Factory is where tenant certificates are renewed.** A deployed tenant needs it once a year, at a
visit or by a request that travels.

**Another site needs no broker, registry or API for tenants** while its tenants are Pis (§8). A site
that hosts tenant workloads would need them, and that is decided when one does.

---

## Alternatives considered

- **Withdrawn: a Tenants CA beside the Site CAs, signing a Service CA and a Device CA per tenant
  (the drafts of 2026-10-21).** It would have given a pinned device a boundary per tenant. It cost an
  online key that makes CAs, two issuers per tenant, a new branch under the root, and devices
  anchored at their tenant's CA. Each of those needed something else: SNI routing, a CA for vanity
  names, and a second secret store. With devices anchored at the root, the per-tenant boundary buys
  nothing on mbedTLS, and the key fingerprint (§5) protects device identity without it.
- **Withdrawn: a shared broker routes by SNI to a listener per tenant, each with the tenant's
  certificate.** The broker is the platform's. Dressing it in each tenant's certificate put keys
  issued for tenant names on the substrate, against ADR-0037 §6.
- **Rejected: a Bus CA under the root for every site's broker.** One more CA, to solve a problem
  that a site-less alias on each broker's own certificate solves (ADR-0040 §4).
- **Rejected: tenant CAs per site.** Two more CAs per site, and a device reissued for every move,
  for a boundary devices cannot enforce.
- **Rejected: a device's bundle adds each site's Substrate CA.** A new anchor for every site a
  device visits. Trusting the root does the same with none.
- **Rejected: a tenant's CA keys move with it between sites** (the first draft).

---

## Open questions

None. Revocation is an accepted risk (R-14), and a tenant at another site is a Deevnet Pi (§8).

---

## What would settle it

The [validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) holds every
test. This record is settled by V1, V2, V3 and V6.
