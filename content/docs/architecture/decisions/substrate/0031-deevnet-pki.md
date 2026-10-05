---
title: "ADR-0031: Deevnet PKI"
weight: -31
---

# ADR-0031: An Offline Deevnet Root, Offline Site CAs, and Separate Substrate and Tenant Device Identity

|  |  |
|--|--|
| **Status** | Accepted (2026-10-05): built by [CHG-0033](/docs/changes/2026/0033-deevnet-pki/). §6, device identity (mTLS), is decided and not yet built: CHG-0034. |
| **Date** | 2026-10-03 |
| **Scope** | The certificate hierarchy for every Deevnet site: the root and each site's CA and who holds them, the issuing CAs and what each may issue, subject names, and the target for tenant device identity (mTLS). Not automatic renewal or expiry alerting ([ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/) open questions 1–2, unchanged). |
| **Supersedes** | ADR-0030 §1–§4 |
| **Amends** | [ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) §3 (the `pki/` row) |
| **Related** | [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) §4, [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §8, [ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/) §2, [ADR-0021](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/) §8, [CHG-0031](/docs/changes/2026/0031-site-root-ca/), [CHG-0032](/docs/changes/2026/0032-appliance-certificates/) |

---

## Context

ADR-0030 gave the site a certificate hierarchy, and CHG-0031 and CHG-0032 built it:

- **a root per site**, its key in the site's ansible-vault;
- **an OpenBao intermediate** issuing to the Platform services;
- **a bootstrap intermediate**, also in the vault, for the core router and the hypervisors, because
  they come up before OpenBao;
- **subjects that carry a CN only.**

In use, it falls short in four ways:

- **The root's key is online in practice.** It sits in the inventory vault, so the vault password
  can mint any certificate the site trusts (risk R-11). The operator wants the root generated and held
  offline by a person.
- **The substrate depends on OpenBao for its own certificates.** The bootstrap intermediate exists only
  to break the cycle that dependency creates. The substrate, bare metal and service VMs alike, is
  meant to be Ansible's alone.
- **There is no device identity.** Devices log in with a username and password (ADR-0012 §8), and
  ADR-0020 §2 left the credential mechanism open. Server identity and device identity have no
  separation in the hierarchy at all.
- **Certificates read poorly.** *Issued To* and *Issued By* show a bare name, with nothing saying what
  organization or which part of it.

## Decision

### 1. One Deevnet Root CA, offline

- One root for the organization, `O=Deevnet, OU=Deevnet PKI, CN=Deevnet Root CA`. RSA 4096, twenty
  years, `pathlen:2`.
- **Generated and maintained offline by the operator**, as a passphrase-encrypted file on two
  offline media
  ([Root of Trust](/docs/runbook/root-of-trust/)). Its key is never on a networked machine.
- It is **the only trust anchor**, on every site.

### 2. A Site CA per site, offline

- Each site has its own, signed by the root: `O=Deevnet, OU=<Site> Site, CN=Deevnet <Site> Site CA`.
  RSA 3072, ten years, `pathlen:1`.
- **Held offline by the same operator, like the root.** It signs only its site's issuing CAs, in a
  ceremony, about every five years.
- **It is name-constrained to Deevnet's own names and private addresses:** DNS `deevnet.net` and
  `localhost`; IP `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `fc00::/7` and
  `::1`. Everything under it, the online Substrate CA included, can vouch for nothing else, so a
  leaked key below the Site CA cannot impersonate a public site to anyone who trusts the Deevnet Root
  CA. The extension is **not marked critical**: mbedTLS, which ESP-IDF and MicroPython use, does not
  implement name constraints and refuses to parse a certificate with a critical extension it does
  not know ([Mbed TLS #3241](https://github.com/Mbed-TLS/mbedtls/issues/3241)). OpenSSL, Go, Java,
  Rust, Erlang, browsers and Windows enforce it either way.
- A Site CA lost is replaced without touching another site or the root's trust. One **exposed** is
  another matter: with no revocation (below), the old one stays valid until it expires.
- **Ceremonies cross the offline boundary on separate transfer media**, never on the key media.
  Tooling moves the request out and the certificate back under hash manifests, refuses any private
  key on the transfer media, and checks the request, the signature and the chain; the decision to
  sign stays the operator's ([Certificates standard](/docs/standards/certificates/) 5.5–5.8).

### 3. Two issuing CAs per site, separating server and device identity

| | Substrate CA | Tenant Device CA |
|---|---|---|
| Subject | `O=Deevnet, OU=<Site> Site, CN=Deevnet <Site> Substrate CA` | `CN=Deevnet <Site> Tenant Device CA` |
| Key | the site's ansible-vault | inside OpenBao, never exported |
| Issued by | Ansible, on the control node | OpenBao, through the Deevnet API |
| Issues | every substrate server certificate, `serverAuth` only | tenant devices' client certificates, `clientAuth` only |

Both are RSA 3072, five years, `pathlen:0`. Each key is generated where it lives, and only its
signing request goes to the ceremony.

### 4. The substrate never depends on OpenBao for a certificate

The Substrate CA issues **every** substrate certificate:
- every bare-metal host and appliance: the core router, the hypervisors, the wireless controller;
- every non-tenant service VM and its services: the API, the broker, the log store, Grafana,
  downloads;
- **OpenBao's own listener.**

A substrate rebuilt from nothing issues all of it before OpenBao exists. The bootstrap intermediate
has no reason left to exist. **ADR-0016 §3's `pki/` row becomes:** issues tenant device certificates
only.

### 5. Subjects carry O, OU and CN

Every certificate's subject is exactly O, OU and CN, in that order:
- servers: `O=Deevnet, OU=<Site> Substrate, CN=<primary FQDN>`;
- devices: `O=Deevnet, OU=Tenant <tenant>, CN=<device>.<tenant>.<site>.deevnet.net`. The CN sits
  inside the Site CA's name constraints: OpenSSL treats a hostname-like CN as a DNS name, and would
  refuse a bare `<device>.<tenant>`.

SANs follow the [Certificates standard](/docs/standards/certificates/):
- a server: its A record, every CNAME and every address, from the inventory;
- a device: exactly one URI, `urn:deevnet:<site>:tenant:<tenant>:device:<device>`.

### 6. Tenant devices are headed for mTLS

The target for ADR-0020 §2's open mechanism and ADR-0012 §8's "PKI a later layer":
- a device's key is generated on the device, or on the tenant's computer for one that cannot, and
  never enters the substrate;
- its signing request goes in through the Deevnet API, for a device the tenant has registered, and
  the Tenant Device CA signs it;
- the broker presents its substrate certificate, and accepts client certificates from the Tenant
  Device CA only;
- it authorizes the device by the URI in its certificate.

Username and password stay until this is built. ADR-0011 §4 holds: device identity only, never
firmware signing.

**ADR-0021's "per-tenant PKI" is answered with one Tenant Device CA per site.** The tenant is in each
certificate's OU and URI, and isolation is the broker's per-identity authorization.

### 7. ADR-0030 §5–§8 stand, issued by the Substrate CA

ADR-0030 §5–§8 stand, with "issued by OpenBao" read as "issued by the Substrate CA, by Ansible":
- one-year leaves, reissued under 60 days;
- certificates laid down by the build and renewed with `certs.yml`;
- trust installed where the tools run;
- the appliances on site certificates.

---

## Consequences

**No online system can mint a CA.** The worst a site can lose is an issuing CA, which the operator
replaces in a ceremony while every client keeps the same anchor. R-11 closes when this is built.

**A substrate rebuild has no cycle.** Everything it needs is Ansible's, so OpenBao goes back to being
a tenant-facing service.

**One trust anchor serves every site.** An operator, a tenant or a device working at more than one
site trusts one root.

**Ceremonies have a cost.**
- **Creating or rotating an issuing CA needs a short offline ceremony**, by the operator, about every
  five years per CA and after any loss of one.
- **A new site needs a longer ceremony**, for its Site CA.

**The site is re-rooted once more.** What CHG-0031/0032 built is replaced:
- the trust anchor changes for every host, image, tenant and computer, once more;
- the OpenBao and bootstrap intermediates retire.

The migration is its own change record.

**Devices get a real identity once this is built.** A stolen password no longer impersonates a
device, and a device is revoked by deregistering it.

**There is no revocation for the CAs.** No CRL or OCSP is published, so an exposed issuing CA or Site
CA stays trusted until its certificate expires: five or ten years. The name constraints bound what a
thief can do with one (Deevnet names and private addresses only), and the
[Custody](/docs/runbook/root-of-trust/custody/#exposed-key) runbook says when an exposure needs a
re-root, the only complete fix.

**The offline machine runs code the online side built.** The ceremony image is built on the Builder,
from packages fetched at build time and scripts from git, and its hash is published by the same
Builder. A compromised Builder could plant code in the image that makes the root. The
[ceremony page](/docs/runbook/root-of-trust/ceremony/#what-this-protects-and-what-it-does-not) says
what is done about it, and what is not.

---

## Alternatives considered

- **Rejected: a public CA** (Let's Encrypt, or a commercial CA), because it cannot certify what a
  site serves. A public CA could cover some of the site's names, but not the parts that matter most:
  - **Public CAs may not certify private addresses or internal names.** Since 2015 publicly trusted
    certificates cannot carry a reserved IP address or an internal name
    ([CA/Browser Forum](https://cabforum.org/working-groups/server/internal-names/)). A site's
    services are dialed at `10.20.x.x`, `127.0.0.1` and `localhost`.
  - **Public CAs no longer issue client certificates.** Let's Encrypt removed TLS client
    authentication from its certificates in 2026, following browser root-program rules
    ([Let's Encrypt](https://letsencrypt.org/2025/05/14/ending-tls-client-authentication)). Device
    identity (mTLS) needs a CA that issues client certificates.
  - **Public certificates cannot say what a certificate is for.** Let's Encrypt issues
    domain-validated certificates only, with no organization ([FAQ](https://letsencrypt.org/docs/faq/)),
    and the organizational unit is no longer permitted in any publicly trusted certificate
    ([Baseline Requirements](https://cabforum.org/working-groups/server/baseline-requirements/requirements/)
    §1.7.9). Deevnet's subjects carry O and OU so that *Issued To* and *Issued By* read plainly.
  - **Public certificates are short-lived by rule, and renewal needs the internet.** Their maximum
    lifetime is 200 days from March 2026, 100 from 2027 and 47 from 2029 (Baseline Requirements
    §6.3.2). Each renewal needs the CA reachable, and a mobile site runs without internet access.
  - **Public certificates publish their names.** Every certificate goes to public Certificate
    Transparency logs, where crawlers find it ([FAQ](https://letsencrypt.org/docs/faq/)). Every host,
    service and tenant name on the site would be listed there.

  A paid CA changes none of these: the rules are the CA/Browser Forum's, and every publicly trusted
  CA follows them. A private PKI's one cost is that nothing trusts its root by default, so the root
  is installed where it is needed
  ([Trust and Identity](/docs/architecture/trust-and-identity/#where-the-deevnet-root-ca-is-trusted)).
  Nothing Deevnet serves is meant for the public internet, so that cost falls only on Deevnet's own
  machines, tenants and operators.
- **Rejected: the Site CA online, in the site's vault.** Fewer ceremonies, but the vault password could
  then mint any CA for the site, and the point of an offline root is lost one level down.
- **Rejected: OpenBao issues the substrate's certificates** (ADR-0030's model). It needs a bootstrap CA
  for what comes before OpenBao, and makes the substrate's rebuild depend on a service the substrate
  builds.
- **Rejected: a root per site** (ADR-0030 §1). Self-contained per site, but every person and device
  working at two sites would carry two anchors. One root with a Site CA per site keeps the per-site
  boundary without that.
- **Not now: one Tenant Device CA per tenant.** Strongest isolation and per-tenant revocation, but a CA
  per tenant to create, rotate and trust. A tenant's devices can move to their own CA later without
  touching anything above the Site CA.
- **Not now: a hardware token for the offline keys.** Stronger custody than encrypted files; the
  ceremony can move to one without changing the hierarchy.

---

## Open questions

1. **Which Site CA issues the Builder's certificate?** `dv00bld001p01` belongs to no site (site code
   `00`), and will need one when it serves the artifact server over TLS.
2. **Where do tenant workloads' own services get server certificates?** From the site, as a third
   issuing CA, or from the tenant itself.
3. **How is a device certificate revoked?** Short-lived certificates, a CRL, or deregistration alone
   (§6).
4. **How does a device that cannot make a key get one?** The tenant's computer generates it (§6); a
   supported way to load it onto such a device is not yet defined.
