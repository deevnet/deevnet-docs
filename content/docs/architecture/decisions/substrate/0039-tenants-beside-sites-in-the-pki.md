---
title: "ADR-0039: Tenants Beside Sites in the PKI"
weight: -39
---

# ADR-0039: A Tenant's PKI Identity Belongs to the Tenant, and the Factory Holds Its Authority

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it) and the [decision register](/docs/architecture/reviews/2026-10-tenant-pki/#decision-register) |
| **Date** | 2026-10-20 |
| **Revised** | 2026-10-21, twice, before review ([Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/)). The first draft moved a tenant's CA keys between sites; that is rejected (§1). Names went to [ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/), the take-home Pi to [ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/), and where the keys are held to [ADR-0042](/docs/architecture/decisions/substrate/0042-pki-and-platform-secrets-separated/). The second revision constrains the Tenants CA to the tenant subtree and qualifies what pinning protects |
| **Scope** | Who holds a tenant's certificate authority, where it sits in the hierarchy, what a device trusts, how a device is bound to its tenant, and how all of that survives the tenant moving. Not names (ADR-0040), not a take-home Pi's own PKI (ADR-0041), not the secret store's deployment (ADR-0042) |
| **Extends** | [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/): a second branch under the root, beside the Site CAs |
| **Amends** | ADR-0031 §3 (the tenant issuing CAs per site), §5 (device subjects and URIs) and §6 (which CA signs a device, and how the broker accepts it); [ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/) §1 and §3; the [Certificates standard](/docs/standards/certificates/) §1 (the tiers, and 1.3's root-only anchor), §3.3, §4, §5 and §6, once accepted |
| **Depends on** | [ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) *(Proposed)* for the tenant subtree; [ADR-0042](/docs/architecture/decisions/substrate/0042-pki-and-platform-secrets-separated/) *(Proposed)* for where its keys live |
| **Related** | [ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/), [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) §4, [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §8, [ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/) §2, [CHG-0034](/docs/changes/2026/0034-device-certificates/), [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) |

---

## Context

**The mobile site is a tenant factory, and it runs on its own.** It travels to meetups, often with
no upstream at all, and never depends on the home site. A tenant is admitted by the operator,
created by one call to the Deevnet API, developed there, and then usually leaves: for the home site,
another Deevnet site, a take-home Pi, or another environment. It may come back for renewal, a new
device, or maintenance.

**Today a tenant's certificates descend from the site it was created on.**
`Deevnet Root CA → Mobile Site CA → Tenant Service CA | Tenant Device CA` (ADR-0031, ADR-0037). Its
names, and the planned device URI (`urn:deevnet:<site>:…`), carry the site. A tenant that moves
changes the CA its certificates chain to, and its devices are provisioned again for a new anchor.

**The root's `pathlen:2` fixes the depth.** Under the root there is room for one CA above every
tenant, the tenant's own CAs below that, and then leaves.

**What constrains any answer** (evidence in the
[review](/docs/architecture/reviews/2026-10-tenant-pki/)):
- **mbedTLS, on most tenant devices, enforces no name constraints.** Constraints are marked
  non-critical so that it parses them at all (ADR-0031 §2).
- **A URN has no host**, so no URI name constraint can bound a device's identity.
- **There is no revocation** (ADR-0031, R-14).
- **The ceremony tools let only a Site CA sign a request**, never the root.
- **The mobile site's OpenBao unseals itself and has no backup.** ADR-0042 is about that.

## Decision

### 1. The factory is the authority for every Deevnet-managed tenant

**A Deevnet-managed tenant's CAs are made at the factory and stay there for the tenant's life.**
Wherever the tenant runs (the mobile site, the home site, another site, a Pi), it is given
certificates. It never inherits the authority. Renewal and new devices come back to the factory as
maintenance (§8).

**A tenant that moves takes no key with it.** Moving is deployment, configuration, networking and
DNS. The first draft of this record exported a tenant's CA keys between sites; that is rejected.

**The factory depends on nothing at the home site.** Nothing here needs a path between sites.

### 2. A Tenants CA beside the Site CAs, and two CAs per tenant

```
Deevnet Root CA (offline, pathlen 2)
├── Deevnet <Site> Site CA (offline, pathlen 1) ── Substrate CA, … (unchanged)
├── Deevnet Tenants CA (factory, pathlen 1; permits t.deevnet.net only)
│     ├── Deevnet <tenant> Service CA (pathlen 0; permits <tenant>.t.deevnet.net)
│     └── Deevnet <tenant> Device CA  (pathlen 0; no name constraint, see §5)
└── Deevnet Names CA (factory, pathlen 0; leaves for vanity names, ADR-0040)
```

**The root signs the Tenants CA once**, in a ceremony:
`O=Deevnet, OU=Deevnet Tenants, CN=Deevnet Tenants CA`, RSA 3072, ten years, `pathlen:1`. Its key is
generated inside the factory's PKI secret store (ADR-0042), and only its request crosses to the
offline signer. The ceremony tools gain the path for the root to sign a request, and file names that
allow a CA with no site.

**When a tenant is created, the Tenants CA signs its two CAs**, automatically, as part of the same
API call, during a PKI session (§9). Their keys are generated in the PKI secret store and never
leave it. Separate Service and Device CAs keep server and device identity apart by signer
(ADR-0031 §3).

| Option | |
|---|---|
| **A. Per-tenant CAs, made online at creation** *(leaning)* | A device pins a key no other tenant shares (§4); a broker can accept a tenant's devices by its own Device CA (§5). Cost: an online key that can make CAs, and two issuers per tenant |
| B. Two shared, site-independent issuing CAs | No online CA-maker. But every tenant's devices share one anchor, so what separates tenants is the API's issuance check alone, and one stolen key forges every tenant |
| C. Per-tenant CAs signed offline | Rejected: a ceremony per tenant, which a meetup cannot wait for |

### 3. The Tenants CA is constrained to the tenant subtree

**It permits `t.deevnet.net` and nothing else** (ADR-0040), and each tenant's Service CA permits only
`<tenant>.t.deevnet.net`. Under RFC 5280 a DNS constraint matches the name itself and every name
below it. A subtree does not age as names are added elsewhere under `deevnet.net`. That is why the
first draft's exclusions of site zones are dropped.

**Vanity names under `deevnet.net` are not the Tenants CA's.** A CA cannot vouch for names outside
its parent's constraints, so they get a CA of their own (the Names CA, ADR-0040).

### 4. What pinning protects, and what it does not

**A device that anchors at its own tenant's Service CA refuses any certificate that does not chain
to that CA's key**, including one from a CA a thief made with a stolen Tenants CA. So a compromised
Tenants CA does not, by itself, defeat a pinned device.

**Everyone else is still exposed.** Browsers, computers and tools anchor at the root. A stolen
Tenants CA key can make a CA that every one of them accepts for any tenant name, and with no
revocation that lasts until the forged CA expires. Constraints keep it inside `t.deevnet.net` for
clients that enforce them, which mbedTLS does not.

**A stolen tenant CA key defeats that tenant's devices.** The pin is only as good as the tenant CA's
custody.

### 5. A device trusts its tenant's Service CA, and is bound to its tenant by the broker

**A device anchors at its tenant's Service CA, not the root.** This amends standard 1.3 for devices
only. Every other client still anchors at the root.

**A device's identity is `urn:deevnet:tenant:<tenant>:device:<device>`**, set by the API from its
registration, never taken from the request.

**Where certificate authentication ends and tenant authorization begins:**
- **Authentication**: the client certificate chains to a tenant's Device CA.
- **Tenant binding**: the URI's tenant is the tenant whose Device CA signed it. Both §6 options
  enforce this at the broker, and a per-tenant listener enforces it in TLS itself (only that
  tenant's Device CA is accepted there).
- **Authorization**: the URI names a device the API has registered and not removed, and its grants
  are that device's topics (ADR-0012 §10).

A valid chain alone authorizes nothing. Deregistering a device is how it is refused, in place of
revocation.

**The Device CAs carry no name constraint.** URI constraints cannot match a URN, and a CA with one
would make Go and OpenSSL refuse every device certificate.

### 6. How a shared broker presents a tenant's certificate: unresolved, two candidates

**The goal is that a device keeps one anchor as its tenant moves.** On a site, devices share the
site's broker, whose certificate today is the site's (Substrate CA).

| Option | |
|---|---|
| **A. SNI routing to a per-tenant listener** *(leaning, pending a proof of concept)* | A stream proxy reads the SNI (`mqtt.<tenant>.t.deevnet.net`) without terminating TLS and passes the connection to that tenant's broker listener. The listener presents a certificate from the tenant's Service CA and accepts client certificates from the tenant's Device CA only. mTLS stays end to end, so no identity has to be carried through a proxy. VerneMQ 2.2.0 supports named SSL listeners, each with its own certificate and CA file; it cannot itself choose a certificate by SNI |
| B. The device's bundle adds the site's Substrate CA | No proxy. But a device is provisioned again for every new site, and its anchor set grows |

**Not chosen: a proxy that terminates TLS.** The broker would then have to trust the proxy's word
for the device's identity, which is the weakening to avoid.

### 7. Lifetimes, rollover and expiry

**The Tenants CA lives ten years, a tenant CA five, a leaf one.** No certificate outlives its issuer.

**A tenant CA is renewed by re-signing the same key**, inside the Tenants CA's validity, before it
expires. **Whether a device still accepts a renewed anchor it does not yet hold** depends on whether
mbedTLS checks an anchor's own dates. That is to be tested. If it does, devices need a way to take a
new anchor every five years, which is the application's (ADR-0011).

**The Tenants CA is renewed by the root**, on the same key, in a ceremony, inside its last five
years.

**A lost key and a compromised key are different events.**
- **Lost:** restore the key from backup (ADR-0042); its identity is unchanged.
- **Compromised:** make a new CA, reissue under it, move every anchor, and accept that the old one
  stays valid until it expires.

### 8. Renewal and enrollment are maintenance, not a connection

**Certificates stay valid while the factory is away.** A deployed tenant needs the factory only to
renew, to add a device, or for maintenance.

**What authorizes a certificate is the tenant's token, never the request.** The API admits a request
only from the tenant or the operator (`ownTenant`). A request and its certificate are public, so
they may travel by any medium: the API directly, a VPN when there is one, or files the owner
carries. A one-year leaf with a 60-day window means a visit every year, inside two months.

### 9. Onboarding has five distinct steps, and a sealed PKI stops it cleanly

1. **The operator admits a tenant name** (exists today).
2. **The operator opens a PKI session**, unsealing the PKI secret store (ADR-0042).
3. **The API creates the tenant and has its two CAs signed**, automatically.
4. **Certificates are issued and renewed** on the tenant's token.
5. **Devices and workloads are authorized** by registration and grants.

**If no PKI session is open, tenant creation refuses before it changes anything**, with an error
that says the PKI is not available. **Creating a tenant's CAs is idempotent**: issuers are named for
the tenant, so an interrupted creation is resumed by the next call, and a reconcile finds a tenant
whose CAs are incomplete.

### 10. Independence is a lifecycle choice, and a trust transition

**A tenant may be Deevnet-managed, become independent, or bring its own PKI.** Independence is a new
authority the tenant holds, its anchors installed beside Deevnet's before Deevnet's are removed.
Deevnet's tenant CA keys are never handed over. The detail is ADR-0041's.

### 11. The site-level tenant CAs retire

**The Mobile Tenant Service CA issues nothing more.** What it issued runs to expiry: `eds`'s console
certificate and CHG-0047's probe certificates. Then its mount is removed. **The Mobile Tenant
Device CA has issued nothing and retires unused.** CHG-0034 is planned again against per-tenant
Device CAs before it is built. Both stay in the platform secret store until removed; nothing moves.

---

## Consequences

**A tenant's names, CAs and device anchor last its whole life.** A move changes where its zone is
answered and where its broker listener runs, not what anything trusts.

**Every person keeps one anchor**, the Deevnet Root.

**The factory is the one place a managed tenant renews.** A tenant that cannot reach it before a
certificate expires is down until it does.

**An online key that can make CAs exists, on a kit that travels.** ADR-0042 keeps it sealed except in
PKI sessions. It remains the hierarchy's weakest point for every relying party that anchors at the
root. The risk register gains a row for it on acceptance.

**The API grows several OpenBao paths**: making a tenant's issuers, having the Tenants issuer sign
them, signing on a tenant's issuers. `sign-intermediate` takes its constraints from the caller, so
the Tenants CA's own constraints, not OpenBao's roles, are what bound a faulty or compromised API.

**Brokers grow per-tenant listeners** (if §6 A is chosen) and a binding check.

**The root signs more than Site CAs**: the Tenants CA and the Names CA. Standard §1 changes.

---

## Alternatives considered

- **Rejected: a tenant's CA keys move with it** (the first draft).
- **Rejected: a Site CA for each place a tenant lives.** Every move is a new Service CA and new
  device anchors.
- **Rejected: the Tenants CA excludes site zones** in place of a subtree. Exclusions fixed at signing
  miss every name added later, and re-signing leaves the old certificate valid.
- **Rejected: the Tenants CA also permits vanity names.** Its bound would become all of
  `deevnet.net`.
- **Rejected: a take-home Pi holds the tenant's Service CA.** A CA key on field hardware.
- **Rejected: devices anchor at the root.** mbedTLS would accept any Deevnet CA's certificate.

---

## Open questions

1. **§6: SNI routing or a Substrate CA in the bundle?** Settled by the proof of concept.
2. **Does mbedTLS check an anchor's own validity dates?** It decides whether devices take a new
   anchor when a tenant CA is renewed.
3. **Does a second site ever create tenants?** If so, does it get a Tenants CA of its own?

---

## What would settle it

The [validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) holds every
test and its acceptance criterion. This record is settled by V1, V2, V3, V5, V6 and V9.
