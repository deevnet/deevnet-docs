---
title: "ADR-0039: Tenants Beside Sites in the PKI"
weight: -39
---

# ADR-0039: A Tenants CA Beside the Site CAs, So a Tenant's Certificates Move With It

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it) |
| **Date** | 2026-10-20 |
| **Scope** | Where a tenant's own CAs sit in the hierarchy, what signs them, which names they may vouch for, what devices and take-home Pis trust, and how the site-level tenant CAs retire. Not revocation, which stays open (ADR-0031), and not who may reach a tenant's service. |
| **Extends** | [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/): a second branch under the root, beside the Site CAs |
| **Amends** | ADR-0031 §3 (the tenant issuing CAs per site), §5 (device subjects and URIs) and §6 (which CA signs a device); [ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/) §1 and §3 (the Tenant Service CA and the zone it issues for); the [Certificates standard](/docs/standards/certificates/) §1, §2, §4, §5 and §6, once accepted |
| **Related** | [ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §13 (a tenant's names), [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) §4, [CHG-0034](/docs/changes/2026/0034-device-certificates/) (device certificates, planned), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) (the Tenant Service CA), the take-home Pi image and [deevnet-kit](/docs/platforms/deevnet-software/deevnet-kit/) |

---

## Context

**A tenant's certificates descend from its site.** The hierarchy is
`Deevnet Root CA → <Site> Site CA → Substrate CA | Tenant Device CA | Tenant Service CA`
(ADR-0031, ADR-0037). The Tenant Service CA issues for `<label>.<tenant>.<site>.deevnet.net`, and
the Tenant Device CA will issue device identities whose URI names the site.

**A tenant does not stay on one site.** A tenant is created on the mobile site, often at a meetup
and always by one call to the Deevnet API. It is developed there, and later it moves: to another
site, or off Deevnet onto its own take-home Pi. Each move today changes the CA its certificates
chain to and the names they carry. Its devices, which hold their broker's CA, are provisioned again.

**A take-home Pi makes a root of its own.** On first boot `deevnet-kit` generates a self-signed CA
for the card and issues the Pi's server certificate from it. Every computer that opens the tenant's
pages then trusts another root, one per tenant, whose key sits on a Pi in someone's house. One root
was chosen so that nobody would do this (ADR-0031 §1).

**The root's path length fixes the depth.** The Deevnet Root CA is `pathlen:2`: two CAs below it,
then a leaf. A branch for tenants therefore has room for one CA above every tenant and the tenant's
own CAs below that, and no more.

**Two certificates are in service under the tenant CAs.** The Mobile Tenant Service CA has issued one
certificate (`eds`'s console). The Mobile Tenant Device CA has issued none: CHG-0034 is planned and
not built.

## Decision

### 1. A Deevnet Tenants CA, beside the Site CAs

**The root signs one more CA, for tenants, at the level of a site:**
`O=Deevnet, OU=Deevnet Tenants, CN=Deevnet Tenants CA`, RSA 3072, ten years, `pathlen:1`. It is
signed in one ceremony, through the existing transfer tools with a `tenants` kind and its own profile.

**Its key is inside OpenBao, so the API signs a tenant's CAs when the tenant is created.** Creating a
tenant stays one API call, with no ceremony and no operator. This is the one CA at its level that is
online; the Site CAs stay offline.

**It is name-constrained, not critically** (mbedTLS, ADR-0031 §2): it permits `deevnet.net` and
`localhost`, and excludes every site's zone. Nothing below it can vouch for a substrate name, whatever
the API or a role does.

| Option | |
|---|---|
| **Online, in OpenBao** *(leaning)* | The only one that keeps onboarding self-service. The cost: an online key that can make CAs, bounded by its constraints |
| Offline, a ceremony per tenant | The strongest custody, but every tenant waits for the operator and the offline media, which a meetup cannot |
| The root signs each tenant directly | No room below for the tenant's two CAs (§2), and the root comes out for every tenant |

### 2. Each tenant has two CAs, made when it is created

**The API has the Tenants CA sign two CAs for each new tenant**, their keys generated inside OpenBao
and never exported to the API:

| | `<tenant> Service CA` | `<tenant> Device CA` |
|---|---|---|
| Subject | `O=Deevnet, OU=Tenant <tenant>, CN=Deevnet <tenant> Service CA` | `O=Deevnet, OU=Tenant <tenant>, CN=Deevnet <tenant> Device CA` |
| Issues | server certificates for the tenant's services and its take-home Pi | its devices' client certificates (mTLS) |
| Usage | `serverAuth` only | `clientAuth` only |
| Names | constrained to `<tenant>.deevnet.net`, `localhost` and loopback | none: a device is named by its URI |

Both are `pathlen:0`, five years. **They replace the site's Tenant Service CA and Tenant Device CA
for that tenant.** The separation of server and device identity (ADR-0031 §3) still rests on which
CA signed, now per tenant.

| Option | |
|---|---|
| **Two CAs per tenant** *(leaning)* | Keeps server and device identity apart by signer, as today |
| One CA per tenant, issuing both | Half the CAs. The separation would rest on an extension in each certificate, which ADR-0037 rejected for the same reason |

### 3. Tenant names drop the site

**A tenant's zone is `<tenant>.deevnet.net`**, and a service is `<label>.<tenant>.deevnet.net`. The
Service CA's constraint is fixed when it is signed, so names that move with the tenant are what make
a move free. The site or the Pi where the tenant lives answers for its zone. A tenant may not be
named after a site code or a reserved zone label.

| Option | |
|---|---|
| **Drop the site** *(leaning)* | One name for the tenant's life |
| Keep the site; constrain the Service CA to each zone the tenant may use | Every new site the tenant moves to means a new Service CA and new trust on its devices |

### 4. Leaves are what ADR-0037 made them

**A leaf is issued as today**: the tenant makes the key; the API reads the request for its public key
alone; one year; renewal by asking again inside 60 days (ADR-0037 §2–§5). Its zone is §3's. **A
device's URI drops the site:** `urn:deevnet:tenant:<tenant>:device:<device>`.

### 5. The site-level tenant CAs retire

**The Mobile Tenant Service CA issues nothing more.** Its one certificate is reissued from
`eds Service CA` on that tenant's next apply, and the mount is removed once nothing it issued is in
service. **The Mobile Tenant Device CA is retired before it issues anything**: CHG-0034 is planned
again against the per-tenant Device CAs before it is built. Browsers and hosts change nothing,
because the root is still their only anchor.

### 6. A tenant's CA keys move between sites once, secret store to secret store

**When a tenant moves to another Deevnet site, its two CA keys are exported once from the source
site's OpenBao and imported into the destination's**, and the source stops issuing for it. They never
pass through the API, a workload or a Pi. This needs the keys created exportable, which no other
tenant CA key is.

| Option | |
|---|---|
| **Move custody once** *(leaning)* | The tenant's CAs live where it lives; the exception is one transfer between two secret stores |
| The site that created the tenant keeps issuing | One site depends on another for every reissue, and the mobile site travels and runs offline |
| New CAs at the destination | Its devices are provisioned again: the cost this record exists to remove |

### 7. A take-home Pi holds a leaf, never a CA

**`deevnet-kit` takes a choice on the card, `pki=`:**

- **`own`**: today's behavior and the default, a CA of the card's own, for a house with no Deevnet;
- **`deevnet`**: the kit makes the key and a request for the tenant's names. The owner sends the
  request through the API from their computer, and the kit installs the leaf with its chain
  (leaf, Service CA, Tenants CA). Renewal is the same each year, and `status` warns at 60 days. No
  CA is on the card, and the server certificate names no `.local` host;
- **`bring`**: the tenant hands in its own CA, or a leaf and its chain. Deevnet trusts none of it.

Losing a Pi then costs one certificate, not a CA.

### 8. Devices trust a bundle, never the root

**A device holds its tenant's Service CA and, while it lives on a site, that site's Substrate CA**,
for the shared broker. mbedTLS does not enforce name constraints, so a device anchored at the root
would accept any Deevnet CA's certificate for its broker's name. With the bundle, a device that moves
needs new Wi-Fi settings and nothing else. On a site, the broker accepts client certificates from the
Tenants branch and authorizes each device by its URI.

---

## Consequences

**A tenant's names, CAs and device trust last its whole life.** A move to another site or to a Pi
changes where its zone is answered and which secret store holds its keys, not what anything trusts.

**Every person keeps one anchor.** A take-home Pi under `pki=deevnet` presents a chain to the Deevnet
Root CA, which every Deevnet computer already trusts.

**An online key can now make CAs.** The Tenants CA is bounded by its constraints and by the API's
single signing grant, as the Tenant Service CA is today, but a CA it signs can itself sign. A tenant
CA key that leaked could vouch for any name in that tenant's zone until it expires. There is no
revocation (ADR-0031).

**Two CAs per tenant is many CAs.** Each is a PKI issuer in OpenBao, made by the API. OpenBao's
policy grants the API one path to have the Tenants CA sign; it cannot read a key or change a role.

**Tenants' names change once.** Every name under `<tenant>.<site>.deevnet.net` moves to
`<tenant>.deevnet.net`, in DNS, in the API and in the provider.

**One more ceremony**, for the Tenants CA, every ten years and after any loss of it.

---

## Alternatives considered

- **Rejected: a Site CA for each place a tenant lives**, with the tenant's CAs under it. Every move
  would be a new Service CA and new device trust.
- **Rejected: every take-home Pi keeps its own root.** One anchor per tenant on every computer, with
  each root's key on a Pi.
- **Rejected: the take-home Pi holds the tenant's Service CA.** A CA key on field hardware; the Pi
  needs one certificate, not the power to make them.
- **Rejected: devices anchor at the Deevnet Root CA.** One file everywhere, but mbedTLS would accept
  any Deevnet CA's certificate for the broker's name.

---

## Open questions

1. **Is the naming change its own record?** It reaches ADR-0015 §13, DNS and the provider, and may
   deserve one.
2. **Does a second site have a Tenants CA of its own**, for tenants created there? Then tenant names
   must be unique across sites.
3. **A two-year leaf for take-home Pis?** Their owner may not reach the API every year.
4. **How does a tenant leave Deevnet completely?** Under `pki=own` or `bring` nothing of Deevnet's
   stays; its devices are then given the tenant's own CA.

---

## What would settle it

1. **On an ESP32**, mbedTLS accepts a CA that is not self-signed as a trust anchor, and a bundle of two
   CAs fits a device's CA field.
2. **OpenBao holds two issuers per tenant**, as mounts or multiple issuers, signed by a Tenants CA
   issuer, with a policy that lets the API sign and nothing more.
3. **Go and OpenSSL refuse** a certificate from a tenant's Service CA for a site's name, and for
   another tenant's.
4. **The Tenants CA ceremony runs** through the existing transfer tools, with its kind and profile.
