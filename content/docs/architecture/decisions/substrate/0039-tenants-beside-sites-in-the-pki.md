---
title: "ADR-0039: Tenants Beside Sites in the PKI"
weight: -39
---

# ADR-0039: A Tenant's PKI Identity Belongs to the Tenant, and the Factory Holds Its Authority

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it) |
| **Date** | 2026-10-20 |
| **Revised** | 2026-10-21, before review: rewritten around the mobile site as an autonomous tenant factory ([Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/)). The first draft moved a tenant's CA keys between sites; that is now rejected (§1). Names moved to [ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/), and the take-home Pi to [ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/) |
| **Scope** | Who holds a tenant's certificate authority, where it sits in the hierarchy, what a device and a hosting site trust, and how that survives the tenant moving. Not the tenant's names (ADR-0040), not a take-home Pi's own PKI (ADR-0041), and not revocation, which stays open (ADR-0031). |
| **Extends** | [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/): a second branch under the root, beside the Site CAs |
| **Amends** | ADR-0031 §3 (the tenant issuing CAs per site), §5 (device subjects and URIs) and §6 (which CA signs a device); [ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/) §1 and §3; the [Certificates standard](/docs/standards/certificates/) §1 (tiers, and 1.3's root-only anchor), §3.3, §4, §5 and §6, once accepted. ADR-0016 §2 as well, if §3's seal option is chosen |
| **Depends on** | [ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) *(Proposed)*: names that do not change when the tenant moves |
| **Related** | [ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) (OpenBao), [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) §4, [ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/) §2, [ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/) *(Proposed)*, [CHG-0034](/docs/changes/2026/0034-device-certificates/), [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) |

---

## Context

**The mobile site is a tenant factory, and it runs on its own.** It travels to meetups, often with
no upstream at all, and never reaches the home site. A tenant is created there by the operator's
admission and one call to the Deevnet API, is developed there, and then usually leaves: for another
Deevnet site, or for a take-home Pi. It may come back for maintenance, for another device, or for
renewal.

**Today a tenant's certificates descend from the site it was created on.**
`Deevnet Root CA → Mobile Site CA → Tenant Service CA | Tenant Device CA` (ADR-0031, ADR-0037). The
names carry the site, and so does the device URI (`urn:deevnet:<site>:…`). A tenant that moves
changes the CA its certificates chain to, and its devices are provisioned again for a new anchor.

**A take-home Pi makes a root of its own.** `deevnet-kit` generates a self-signed CA on first boot,
so every computer that opens the tenant's pages trusts one more root, whose key is on a Pi in
someone's house.

**The root's `pathlen:2` fixes the depth.** Under the root there is room for one CA above every
tenant, the tenant's own CAs below that, and then leaves.

**Several facts constrain any answer** (detail in the
[review](/docs/architecture/reviews/2026-10-tenant-pki/)):
- **OpenBao on the mobile site unseals itself.** The static seal key sits on the same host as the
  data, and nothing backs that data up (ADR-0016 §2; the backup runbook says "Nothing yet").
- **mbedTLS, on most tenant devices, enforces no name constraints.**
- **A URN has no host**, so no URI name constraint can bound a device's identity.
- **The ceremony tools let only a Site CA sign a request**, never the root.

## Decision

### 1. The factory is the authority for every Deevnet-managed tenant

**A Deevnet-managed tenant's CAs are made on the mobile site and stay there for the tenant's life.**
Sites that host the tenant, and take-home Pis, are given certificates. They never inherit the
authority. Renewal and new devices come back to the factory as maintenance (§7).

**A tenant that moves takes no key with it.** Moving is deployment, configuration, networking and
DNS. The first draft of this record exported a tenant's CA keys from one site's secret store into
another's; that is rejected: custody does not follow workloads.

**The factory depends on nothing at the home site.** Nothing in this record needs a network path
between sites.

### 2. A Tenants CA beside the Site CAs, and two CAs per tenant

```
Deevnet Root CA (offline, pathlen 2)
├── Deevnet <Site> Site CA (offline) ── Substrate CA, … (unchanged)
└── Deevnet Tenants CA (mobile site, online, pathlen 1)
      ├── Deevnet <tenant> Service CA (pathlen 0) ── the tenant's server certificates
      └── Deevnet <tenant> Device CA  (pathlen 0) ── its devices' client certificates
```

**The root signs the Tenants CA once**, in a ceremony:
`O=Deevnet, OU=Deevnet Tenants, CN=Deevnet Tenants CA`, RSA 3072, `pathlen:1`. The ceremony tools
gain a path for the root to sign a request; today they have none.

**The API has it sign a tenant's two CAs when the tenant is created.** Creating a tenant stays one
call after admission, with no ceremony and no operator beyond the admission that already exists.

| Option | |
|---|---|
| **A. Per-tenant CAs, made online at creation** *(leaning)* | A device pins a key that no other tenant shares (§5), and the broker binds a device to its tenant by signer (§6). The cost: an online key that can make CAs (§3), and two issuers per tenant in OpenBao |
| B. Two site-independent issuing CAs shared by every tenant | No online CA-maker: the online keys issue only leaves, and a lost one is one ceremony. But a device's anchor is shared by every tenant, so what keeps tenant B from passing as tenant A's broker is the API's issuance check alone, and a stolen key forges every tenant |
| C. Per-tenant CAs signed offline | The strongest custody. Rejected: every tenant would wait for a ceremony, which a meetup cannot |

**Two CAs per tenant are kept for the same reason the site has two**: server and device identity
are separated by signer, not by an extension (ADR-0031 §3, ADR-0037's alternatives). The cost is
issuers. OpenBao holds many issuers on one mount, so a tenant is two issuers and two roles, not two
mounts.

### 3. The Tenants CA is the riskiest key in the hierarchy, and is held accordingly

**It is online, it can make CAs, and it travels.** A stolen copy can make a CA for any tenant name,
and with no revocation (ADR-0031) that CA stays valid until it expires. Its name constraints bind
browsers, Go and OpenSSL; they do not bind mbedTLS (§4).

**Its key is generated on the control node, held in ansible-vault and imported into OpenBao**, by
CHG-0036's rule for keys that can't be re-derived. A rebuilt OpenBao gets it back without a
ceremony, and nothing that chains to it changes.

| Option | |
|---|---|
| **Generated on the control node, kept in the vault** *(leaning)* | Recoverable, as CHG-0036 already agreed for the Tenant Device CA. It means a second copy, as the Substrate CA's key has (R-13) |
| Generated inside OpenBao, never exported | One copy, but a lost OpenBao means a new Tenants CA, a root ceremony, and every tenant's CAs made again |

**Per-tenant CA keys are generated inside OpenBao** (the API makes them at runtime, so they can't
come from the vault). They are recovered from **Raft snapshots kept off the kit**
(INC-0003 action 6, not built).

**The seal is the open hardening question.** Today the kit restarts unattended because its seal
key is on the same host. With an online CA-maker, a stolen kit is a stolen authority. Options,
recorded and not decided here:
- unseal by an operator at each start;
- a seal key carried apart from the kit (a removable token);
- keep the static seal and accept the risk in the register.

**Its lifetime outlasts the CAs it signs**: ten years, against five for a tenant CA. A tenant CA is
reissued, on the same key, inside the Tenants CA's last five years.

### 4. Constraints are a second line, not the boundary

**The Tenants CA permits only tenant names** (ADR-0040 decides their shape) and `localhost`, and
each tenant's Service CA permits only its own zone. Both are marked non-critical, so that mbedTLS
parses them (ADR-0031 §2).

**What they do not do is stated, so nothing leans on it:**
- **mbedTLS enforces none of them.**
- **A device's URN can't be constrained**: Go and OpenSSL match a URI constraint against a host,
  and a URN has none. The Device CAs carry no URI constraint.
- **An exclusion is fixed at signing.** A name added under `deevnet.net` later is not excluded, and
  re-signing on the same key leaves the old certificate valid. This is why ADR-0040 weighs a tenant
  subtree.

**The boundaries that hold are §5's pinned anchor and §6's binding check.**

### 5. A device trusts its tenant's Service CA, and a site presents the tenant's certificate

**A device anchors at its tenant's Service CA, not the root.** mbedTLS checks a chain against the
anchor's key, so a CA made with another key, under any name, is refused. This amends standard 1.3,
which allows only the root.

**A site's shared broker presents a certificate issued by the tenant's authority**, for the tenant's
broker name, chosen by SNI. The site generates the key and asks the factory for the certificate, as
any host does. "Certificates travel; authorities remain": a device dials its tenant's name
wherever it is, and its anchor never changes.

| Option | |
|---|---|
| **The site presents a tenant-issued certificate, by SNI** *(leaning)* | One anchor for the device's life, on a site or a Pi. The cost: the broker, or a stream proxy in front of it, must choose a certificate by SNI (to confirm), and a site holds keys for names in tenant zones |
| The device's bundle adds the Substrate CA of each site it uses | No SNI. But a device is provisioned again for every new site, which this record exists to avoid, and the bundle grows |
| The device anchors at the root | One file everywhere. Any Deevnet CA's certificate passes for the broker's name: rejected |

### 6. Device identity is bound to its tenant by the broker

**A device's URI drops the site:** `urn:deevnet:tenant:<tenant>:device:<device>`, set by the API,
never taken from the request.

**A broker accepts device certificates from the Tenants branch, and refuses any whose URI names a
tenant other than the one whose Device CA signed it.** That check is the boundary, because no
constraint can bound a URN (§4). It is the broker's, on a site and on a Pi alike.

### 7. Renewal and enrollment are maintenance, not a connection

**Certificates stay valid while the factory is away.** A deployed tenant needs the factory only to
renew or to add a device.

**What authorizes a certificate is the tenant's token, never the request.** The API already admits a
request only from the tenant itself or the operator (`ownTenant`). A request and its certificate are
public, so they may travel by any medium: the API directly, a VPN when there is one, or files
carried by the owner.

**A one-year leaf and a 60-day window mean a visit every year, inside two months.** Recorded as a
consequence, with the option of longer leaves for a tenant that does not live on a site
(ADR-0041), up to what clients accept.

### 8. Independence is a lifecycle choice, and a trust transition

**A tenant may be Deevnet-managed, become independent, or bring its own PKI**, and may change
between them. Independence is a new authority that the tenant holds, its anchors installed beside
Deevnet's, its certificates reissued, and Deevnet's anchors retired. Deevnet's tenant CA keys are
never handed over. The take-home detail is ADR-0041's.

### 9. The site-level tenant CAs retire

**The Mobile Tenant Service CA issues nothing more.** What it issued runs to expiry: `eds`'s console
certificate and CHG-0047's probe certificates, which its check reissues on every run. Then its mount
is removed. **The Mobile Tenant Device CA has issued nothing and retires unused.** CHG-0034 is
planned again against the per-tenant Device CAs before it is built. Browsers and hosts change
nothing: they still anchor at the root.

---

## Consequences

**A tenant's names, CAs and device anchor last its whole life.** A move changes where its zone is
answered, not what anything trusts.

**Every person keeps one anchor**, the Deevnet Root, for the tenant's pages wherever they are served.

**The factory is the one place a managed tenant renews.** A tenant that cannot reach it before a
certificate expires is down until it does.

**An online key on a travelling kit can make CAs.** It is the hierarchy's weakest point. Its
custody (§3) and the seal question are what decide how weak; the risk register gains a row for it on
acceptance.

**The API grows from one OpenBao path to several**: making a tenant's issuers, having the Tenants
issuer sign them, and signing on a tenant's issuer. `sign-intermediate` takes the constraints from
its caller, so the Tenants CA's own constraints, not OpenBao, are what bound a faulty or compromised
API.

**Brokers carry tenant-issued certificates and check device bindings**, on every site and Pi.

**Two ceremonies' worth of tooling change**: the root signs a request, and file names allow a CA
with no site (standard §6).

---

## Alternatives considered

- **Rejected: a tenant's CA keys move with it** (this record's first draft, §6). Custody would change
  with every move, and a key would cross between secret stores.
- **Rejected: a Site CA for each place a tenant lives.** Every move is a new Service CA and new
  device anchors.
- **Rejected: every take-home Pi keeps its own root** as the managed default. One anchor per tenant
  on every computer, with each root's key on a Pi. It stays available as a choice (ADR-0041).
- **Rejected: a take-home Pi holds the tenant's Service CA.** A CA key on field hardware; the Pi
  needs a certificate, not an authority.
- **Rejected: devices anchor at the root.** mbedTLS would accept any Deevnet CA's certificate.

---

## Open questions

1. **How is the kit sealed?** §3's three options.
2. **Can the broker choose a certificate by SNI**, or does a stream proxy front it?
3. **Does a second site ever create tenants?** If so, does it get a Tenants CA of its own, and must
   tenant names be unique across sites?
4. **How is a tenant CA reissued** when the Tenants CA is renewed, and do devices need anything?

---

## What would settle it

The [review](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) holds the full plan.
This record is settled by:
1. **On an ESP32**, mbedTLS accepts a tenant's Service CA (not self-signed) as its only anchor, and
   refuses a CA with the same subject and another key.
2. **On OpenBao**, a mount holds two issuers per tenant under a Tenants issuer; `sign-intermediate`
   writes the constraints asked for; a snapshot restored to an empty instance keeps them all.
3. **Go and OpenSSL refuse** a tenant CA's certificate for a site's name and for another tenant's.
   They refuse a URN under a URI constraint, which is the reason §6's check is the broker's.
4. **The mobile site with no upstream** creates a tenant, signs its CAs, issues a leaf, and enrolls a
   device.
5. **A tenant moves** from the mobile site to a Pi and back, and no CA, anchor or key changes.
