---
title: "CHG-0034: Device Certificates Through the Deevnet API"
weight: -34
---

# CHG-0034: Device Certificates Through the Deevnet API

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. After [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) (the re-keyed Tenant Device CA) and [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/) (the reserved `device` label) |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API), `dv02idn001v01` (the Tenant Device CA in OpenBao), `dv02msg001v01` (the broker); the provider; a tenant's device |
| **Automation** | `deevnet-provisioning-api`, `terraform-provider-deevnet`, `deevnet.mgmt` `site.yml --tags vernemq,deevnet-api` |
| **Risk** | Medium. Most likely to go wrong: turning on client certificates at the broker locks out devices still using passwords. Both stay accepted until every device has moved |
| **Related changes** | [CHG-0044](/docs/changes/2026/0044-tenant-device-addresses/) (device addresses, done first; independent of this), [CHG-0033](/docs/changes/2026/0033-deevnet-pki/) (built the Tenant Device CA), [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) (its key from the vault), [CHG-0016](/docs/changes/2026/0016-broker-accounts/) |
| **Related incidents** | None |
| **Related runbooks** | [Devices and MQTT](/docs/runbook/tenant/services/devices-and-mqtt/), [Connect a Device](/docs/runbook/tenant/connect-a-device/) |

---

## Summary

[ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/) §6 sets the target for device
identity: a device's key is made on the device, or on the tenant's computer for one that can't, and
never enters the substrate. Its signing request goes in through the Deevnet API for a device the tenant
has registered, and the Tenant Device CA signs it. Until this is built, devices use a username and
password. CHG-0033 built the Tenant Device CA and reserved this record for the rest.

**Re-planned for the site-less identity of
[ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/) §4–§5**
([review](/docs/architecture/reviews/2026-10-tenant-pki/), phase P6). A device's certificate is its
passport and names no site: its URI is `urn:deevnet:tenant:<tenant>:device:<device>` and its CN
`<device>.device.<tenant>.deevnet.net`. Its registration at a site is its visa. The broker admits a
device only if its certificate chains to the Tenant Device CA, its URI names a device registered at
this site, and its public key matches the fingerprint recorded when the certificate was issued. The
fingerprint is what makes a stolen Tenant Device CA key not enough.

A device certificate is public, so a tenant can keep it in its repository: a device that holds its own
key never needs the substrate to remember a secret for it.

## Goal

- A registered device's signing request, submitted through the provider, comes back signed by the
  Tenant Device CA, with the tenant in its OU, its site-less URI and its CN under the `device` label,
  all set from the registration, never from the request.
- The API records the certificate's public key fingerprint against the device's registration.
- The broker presents its substrate certificate and accepts client certificates from the Tenant Device
  CA only, admitting a device by the three checks and granting it the same topics a password account
  gets.
- Password accounts keep working beside certificates until a tenant moves its devices.
- One real device (mabell's gateway, or eds's stand) connects with a certificate.
- ADR-0031 §6 is built.

## Scope

**In scope:** the signing route, the fingerprint record, the provider resource, the broker's
client-certificate listener and its three checks, one device moved.
**Out of scope here, built later:** the same checks on a Deevnet Pi's broker
([CHG-0056](/docs/changes/2026/0056-kit-deevnet-or-own-pki/)).
**Out of scope:** retiring passwords site-wide; revocation, accepted as risk R-14: deregistering a device is how it is refused; loading keys onto devices that can't make one, which is open question 4.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Password devices locked out | the broker | Certificates on a separate listener or alongside passwords; nothing removed in this change |
| A certificate authorizes more than its device | the broker | Authorization by URI to exactly the account's topics; tested with a certificate for another tenant's device |
| A forged certificate for a registered device's URI | the broker | The fingerprint check; tested with a certificate for a registered URI and another key |
| The Tenant Device CA key lost on an OpenBao rebuild | OpenBao | CHG-0036 first: the key comes from the vault |

## Prerequisites

- [x] CHG-0036 and CHG-0054 complete (2026-10-25 and 2026-11-07)
- [ ] A device whose firmware can present a client certificate, and its tenant's agreement

## Procedure

### Step 1: The signing route

The API signs a registered device's request with the Tenant Device CA, setting the subject, CN and
URI itself and ignoring what the request asks for, and records the key's fingerprint.

**Verify:** integration tests: a registered device gets a certificate with a site-less URI and its
fingerprint recorded; an unregistered one, or another tenant's, is refused.

### Step 2: The provider

A device certificate resource that takes a request and returns the certificate.

### Step 3: The broker

Client certificates from the Tenant Device CA accepted, checked against the site's registrations and
recorded fingerprints, and authorized by URI to the device's topics.

**The checks run beside the broker, never in the API.** ADR-0012 §8 keeps the API out of a device's
path: an API outage stops provisioning, never devices. So the design found for VerneMQ 2.2.0 (see
[To discover](#to-discover)) is:

- **A second TLS listener for certificates**, beside the password listener on 8883:
  `require_certificate = on`, trusting the Tenant Device CA only, with `forward_connection_opts = on`
  so the hooks receive the client's certificate. The password listener is unchanged, so no device
  is locked out.
- **A small authentication service on the messaging VM**, on loopback, which VerneMQ's webhooks
  plugin calls for `auth_on_register` (and the MQTT 5 variant) on that listener only. It decodes the
  certificate, takes its URI, looks the device up in the broker's own database, and compares the
  SHA-256 of the certificate's public key with the fingerprint recorded there.
- **The API writes that row when it signs**, as it writes a password account today: the device's
  URI, its tenant and the fingerprint. Deregistering a device deletes the row.

Two behaviors are proven on a test broker before this step is built: that the webhook can answer
`next` for the password listener so `auth_postgres` still handles it, and how publish and subscribe
are authorized for a session the webhook admitted (`auth_postgres` caches a password session's
grants when it registers).

**Verify:** V6: a certificate for a registered URI with another key, a device not registered at this
site and a deregistered device are refused; a test client with a genuine certificate publishes to its
own topics and is refused another tenant's.

### Step 4: One real device

Move one device to a certificate, its key made on the device.

**Verify:** it connects and publishes; its password account can then be removed.

## Verification

Step 4 passes, a certificate for one tenant's device can't reach another tenant's topics, and V1 and
V6 of the [validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass.

## Undo

Disable the certificate listener; password accounts were never removed.

## To discover

**Found 2026-11-21, from VerneMQ's source at its `2.2.0` tag and its documentation:**

- **VerneMQ itself reads only the certificate's common name.** With `use_identity_as_username`, the
  subject's CN replaces the username the client sent (`vmq_ranch.erl`, `vmq_ssl.erl`); no
  subjectAltName is read. The client's password still goes to the hooks.
- **The whole certificate reaches a plugin only with `forward_connection_opts`.** Then
  `auth_on_register` gets it as `client_cert` (the webhook payload carries it base64-encoded), and
  nothing derived from it: no URI, no public key, no fingerprint. So the URI and fingerprint checks
  are the plugin's, from the certificate itself.
- **`auth_postgres`, the broker's present authentication, refuses a client with no password**
  (`postgres_cockroach_commons.lua`), so a certificate-only device needs another plugin.
- **A Lua plugin is not the place to parse a certificate.** The Lua runtime receives the raw DER and
  has no X.509 parser (inferred, not tried); the webhook gets the same certificate in a form any
  language can parse.
- **`allow_anonymous_override` on a listener skips every authentication hook**, so the certificate
  listener must not set it.
- **Revocation is possible after all:** `listener.ssl.<name>.crlfile` checks a CRL at the TLS
  handshake. R-14 accepts deregistration as the only way to refuse a device; a CRL from the Tenant
  Device CA would add one. Not in this change.

**The first device is EdS's cover screen** (ESP32-2432S028R, ESP-IDF 6, `espressif/mqtt`). Its
credentials already live in an NVS partition of their own, `creds`, which holds the Wi-Fi settings,
the broker's address and login, and the CA. The plan:
it makes a P-256 key on first start and keeps it in `creds`, prints a signing request over serial
for the tenant's Terraform, takes the signed certificate back into `creds` the way its other
credentials are written, and gives both to the MQTT client. Its password login stays until the
certificate works. To check on the board: free memory with TLS up and a client certificate loaded
(about 100 KB is free today), and the MQTT client's field names for a client certificate and key in
the component's current version.

## To close

**What is left before this change closes, from its procedure and verification.**

- [ ] Step 1: the API signs a registered device's request with the Tenant Device CA and records its key fingerprint
- [ ] Step 2: a device certificate resource in the provider
- [ ] Step 3: the broker accepts Tenant Device CA certificates, checked against registrations and fingerprints (V6)
- [ ] Step 4: one real device on a certificate, its key made on the device
- [ ] Verification: a device's certificate can't reach another tenant's topics, and V1 and V6 of the [validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass
