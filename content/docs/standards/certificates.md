---
title: "Certificates"
weight: 7
---

# Deevnet Certificates Standard

### Purpose

This standard defines what every Deevnet X.509 certificate looks like: who may issue it, what its
subject and names say, which keys and lifetimes it uses, and where its key may live. The model it
serves is in [Trust and Identity](/docs/architecture/trust-and-identity/) and
[ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/).

A certificate that does not meet this standard is a defect, whatever issued it.

---

## 1. Four tiers: Root CA, Site CA, issuing CA, end entity

| Tier | Issued by | Signs | Count |
|---|---|---|---|
| **Root CA** | itself | Site CAs only | one, for the organization |
| **Site CA** | the Root CA | that site's issuing CAs only | one per site |
| **Issuing CA** | its Site CA | end-entity certificates only | per site: the **Substrate CA** and the **Tenant Device CA** |
| **End entity** | an issuing CA | nothing | servers and devices |

- 1.1 A Root CA MUST NOT sign an end-entity certificate, and a Site CA MUST NOT sign one.
- 1.2 The Substrate CA MUST issue only server certificates for the substrate. The Tenant Device CA
  MUST issue only client certificates for tenant devices.
- 1.3 Every client MUST trust the Root CA as its anchor. A client MUST NOT be configured to trust a
  Site CA or an issuing CA as an anchor in its place.

---

## 2. Every subject is exactly O, OU and CN

Every subject MUST carry exactly **O**, **OU** and **CN**, encoded in that order, so that a
certificate's *Issued To* and *Issued By* each name the organization, the part of it, and the thing
itself.

| Certificate | O | OU | CN |
|---|---|---|---|
| Root CA | `Deevnet` | `Deevnet PKI` | `Deevnet Root CA` |
| Site CA | `Deevnet` | `<Site> Site` | `Deevnet <Site> Site CA` |
| Substrate CA | `Deevnet` | `<Site> Site` | `Deevnet <Site> Substrate CA` |
| Tenant Device CA | `Deevnet` | `<Site> Site` | `Deevnet <Site> Tenant Device CA` |
| Substrate server | `Deevnet` | `<Site> Substrate` | the host's primary FQDN, e.g. `pve.mobile.deevnet.net` |
| Tenant device | `Deevnet` | `Tenant <tenant>` | `<device>.<tenant>`, e.g. `lp-stand-01.eds` |

- 2.1 `<Site>` MUST be the site's name in title case, as in the [naming standard](/docs/standards/naming/):
  `Mobile`, `Home`.
- 2.2 `<tenant>` and `<device>` MUST be the names the Deevnet API holds, exactly.
- 2.3 Subjects MUST NOT carry C, ST, L or an email address.

---

## 3. A certificate is valid for the names and addresses its clients dial

A client checks the name it dialled against the SANs, never the CN. The SANs are what a certificate
is valid for.

- 3.1 A substrate server certificate MUST carry, as DNS SANs, the host's A record and every CNAME of
  it, and, as IP SANs, every address it serves on. They MUST be derived from the inventory, the same
  data the site's DNS is published from, never written by hand.
- 3.2 A server certificate MAY carry more where a client dials it so: `localhost`, `127.0.0.1`, or a
  router's gateway addresses on every segment.
- 3.3 A tenant device certificate MUST carry exactly one URI SAN:
  `urn:deevnet:<site>:tenant:<tenant>:device:<device>`, lower case. It is the identity a service
  authorizes. It MUST NOT carry a DNS or IP SAN.

---

## 4. Each tier has a fixed key, lifetime and set of extensions

| Tier | Key | Lifetime | basicConstraints | keyUsage | extendedKeyUsage |
|---|---|---|---|---|---|
| Root CA | RSA 4096 | 20 years | `critical, CA:TRUE, pathlen:2` | `critical, keyCertSign, cRLSign` | — |
| Site CA | RSA 3072 | 10 years | `critical, CA:TRUE, pathlen:1` | `critical, keyCertSign, cRLSign` | — |
| Issuing CA | RSA 3072 | 5 years | `critical, CA:TRUE, pathlen:0` | `critical, keyCertSign, cRLSign` | — |
| Substrate server | RSA 2048; P-256 where every client of it supports ECDSA | 1 year | `critical, CA:FALSE` | `critical, digitalSignature, keyEncipherment` | `serverAuth` only |
| Tenant device | P-256, or RSA 2048 where the device cannot do ECDSA | 1 year | `critical, CA:FALSE` | `critical, digitalSignature` | `clientAuth` only |

- 4.1 RSA throughout the CA tiers keeps the chain verifiable by the oldest device TLS stacks on the
  site.
- 4.2 Signatures MUST use SHA-256 or stronger.
- 4.3 Every certificate below the root MUST carry `authorityKeyIdentifier`, and every CA
  `subjectKeyIdentifier`.
- 4.4 Serial numbers MUST be random, at least 64 bits.
- 4.5 A certificate MUST NOT carry both `serverAuth` and `clientAuth`. Server identity and device
  identity are different things, issued by different CAs.
- 4.6 Extensions MUST come from the issuer's profile. An issuer MUST NOT copy extensions from a
  signing request.
- 4.7 An end-entity certificate MUST be reissued once fewer than 60 days remain.

---

## 5. Each key lives in exactly one allowed place

| Key | Where | Generated |
|---|---|---|
| Root CA, Site CA | passphrase-encrypted files on two offline media, generated and maintained offline; never available to site automation or networked systems | on an offline machine ([Root of Trust](/docs/runbook/root-of-trust/)) |
| Substrate CA | the site's ansible-vault | by automation, on the control node |
| Tenant Device CA | the site's secret store; it never leaves | inside the secret store |
| Substrate server | the server it identifies | by automation, then installed |
| Tenant device | the device | on the device, or on the tenant's own computer for a device that cannot |

- 5.1 The Root CA's and every Site CA's key MUST NOT be present on a networked machine, in any form.
- 5.2 An issuing CA's key MUST be generated where it lives. Only its signing request travels to be
  signed.
- 5.3 A tenant device's key MUST NOT enter the substrate. The device's signing request does; the
  issued certificate goes back. This is [Secure Identity](/docs/standards/secure-identity/) 3.1
  applied to devices.
- 5.4 The substrate's certificates MUST NOT depend on the secret store. The Substrate CA is
  automation's, so a substrate rebuilt from nothing can issue every certificate it needs before the
  secret store exists.

### Only the transfer media crosses the offline boundary

- 5.5 The media holding the Root CA's and Site CAs' keys (the *key media*) MUST be used only on the
  offline machine, and MUST NOT be the media that carries anything between the online and offline
  machines.
- 5.6 Only the *transfer media* crosses. It MUST carry only signing requests, certificates, the
  signing profile and the ceremony's tools. It MUST NOT carry a private key.
- 5.7 What crosses MUST travel under a manifest of SHA-256 hashes, checked on arrival on each side.
  A request is signed only after its subject and signature are checked and the key holder confirms
  it. A returned certificate is installed only after it is checked against the original request's
  key and chained to the Root CA through the **online side's own** copies of the Root and Site CA
  certificates.
- 5.8 The ceremony's tools (`deevnet-pki-transfer.sh`, `deevnet-pki-sign.sh`) enforce 5.5–5.7. Tooling
  MAY automate the mechanics and the checks, and MUST NOT automate the decision to sign.
- 5.9 The offline machine MUST have its radios disabled and no network service running, and MUST NOT
  carry an automation account or remote access. Its clock MUST be checked before any key or
  certificate is made. Its operating system SHOULD be the image factory's ceremony image (`pi-pki`),
  checked against its published hash before use, so that the code that signs is pinned at build and
  never arrives on the transfer media.

---

## 6. Files are named deevnet-<site>-<ca>.pem

| File | Holds |
|---|---|
| `deevnet-root-ca.pem` | the Root CA's certificate |
| `deevnet-<site>-site-ca.pem` | a Site CA's certificate |
| `deevnet-<site>-substrate-ca.pem` | a Substrate CA's certificate |
| `deevnet-<site>-tenant-device-ca.pem` | a Tenant Device CA's certificate |

`<site>` is lower case: `deevnet-mobile-site-ca.pem`. A key file is named for its certificate with
`.key`.

---

## 7. A certificate is correct only when all of these hold

A Deevnet certificate is correct when:

- it chains to the Deevnet Root CA through its Site CA and exactly one issuing CA;
- its subject is exactly O, OU and CN, as in section 2;
- it is valid for every name and address its clients dial, and nothing it could not be dialled by;
- it is either a server certificate or a client certificate, never both;
- its key has never been anywhere this standard does not allow.
