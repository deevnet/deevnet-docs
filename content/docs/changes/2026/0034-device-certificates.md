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
| **Window** | Unscheduled. After [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) |
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
has registered, the Tenant Device CA signs it, and the broker accepts client certificates from that CA
alone, authorizing each device by the URI in its certificate,
`urn:deevnet:<site>:tenant:<tenant>:device:<device>`. Until this is built, devices use a username and
password. CHG-0033 built the Tenant Device CA and reserved this record for the rest.

A device certificate is public, so a tenant can keep it in its repository: a device that holds its own
key never needs the substrate to remember a secret for it.

## Goal

- A registered device's signing request, submitted through the provider, comes back signed by the
  Tenant Device CA, with the tenant in its OU and the device's URI.
- The broker presents its substrate certificate and accepts client certificates from the Tenant Device
  CA only, authorizing by URI to the same topics a password account gets.
- Password accounts keep working beside certificates until a tenant moves its devices.
- One real device (mabell's gateway, or eds's stand) connects with a certificate.
- ADR-0031 §6 is built.

## Scope

**In scope:** the signing route, the provider resource, the broker's client-certificate listener and
its authorization by URI, one device moved.
**Out of scope:** retiring passwords site-wide; revocation beyond deregistration, which is ADR-0031's
open question 3; loading keys onto devices that can't make one, which is open question 4.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Password devices locked out | the broker | Certificates on a separate listener or alongside passwords; nothing removed in this change |
| A certificate authorizes more than its device | the broker | Authorization by URI to exactly the account's topics; tested with a certificate for another tenant's device |
| The Tenant Device CA key lost on an OpenBao rebuild | OpenBao | CHG-0036 first: the key comes from the vault |

## Prerequisites

- [ ] CHG-0036 complete
- [ ] A device whose firmware can present a client certificate, and its tenant's agreement

## Procedure

### Step 1: The signing route

The API signs a registered device's request with the Tenant Device CA, setting the subject and URI
itself and ignoring what the request asks for.

**Verify:** integration tests: a registered device gets a certificate; an unregistered one, or another
tenant's, is refused.

### Step 2: The provider

A device certificate resource that takes a request and returns the certificate.

### Step 3: The broker

Client certificates from the Tenant Device CA accepted, and authorized by URI to the device's topics.

**Verify:** a test client with a certificate publishes to its own topics and is refused another
tenant's.

### Step 4: One real device

Move one device to a certificate, its key made on the device.

**Verify:** it connects and publishes; its password account can then be removed.

## Verification

Step 4 passes, and a certificate for one tenant's device can't reach another tenant's topics.

## Undo

Disable the certificate listener; password accounts were never removed.

## To discover

- How VerneMQ maps a client certificate's URI to an identity it authorizes, against its current
  documentation.
- What each tenant's device hardware and firmware can do: make a key, present a certificate.
