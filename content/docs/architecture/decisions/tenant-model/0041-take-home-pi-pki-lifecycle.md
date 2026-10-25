---
title: "ADR-0041: Take-Home Pi PKI Lifecycle"
weight: -41
---

# ADR-0041: A Take-Home Pi Is a Deevnet Pi by Default, and Carries a Starter Kit for a PKI of Its Own

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it) and the [decision register](/docs/architecture/reviews/2026-10-tenant-pki/#decision-register) |
| **Date** | 2026-10-21 |
| **Revised** | 2026-10-21, before review, and 2026-10-25 in the [Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/). The drafts of 2026-10-21 gave a card three modes (`deevnet`, `own` as the generic default, `bring`). That is withdrawn for one default and a starter kit |
| **Scope** | The certificates on a take-home Pi and its devices: what the card is given, what an owner who leaves Deevnet uses to make a PKI of their own, and how the card's first-boot configuration chooses between them. Not the tenant CAs ([ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/)), not names ([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/)) |
| **Depends on** | ADR-0039 *(Proposed)* and ADR-0040 *(Proposed)* |
| **Related** | [ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/) §4, [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/), the [take-home Pi image](/docs/runbook/tenant/tenant-to-pi-image/), [deevnet-kit](/docs/platforms/deevnet-software/deevnet-kit/) |

---

## Context

**A take-home Pi is a small Deevnet of the tenant's own**: broker, log store and Grafana on one card,
with `deevnet-kit` doing what the API does on a site. One generic image is built and published to
the tenant downloads, and the tenant is set on the card at first boot.

**Today the card makes its own CA at first boot**, ten years, and issues the Pi's server certificate
from it, 825 days, for the card's `.local` name, `localhost` and its addresses. Apps and devices
are pointed at the exported `deevnet-kit-ca.pem`. There is no other mode.

**The offline ceremony tools already exist** (`deevnet.mgmt` `scripts/pki/`): a root and a Site CA
on encrypted key media, issuing CAs signed across a transfer drive. They are written for Deevnet's
names.

## Decision

### 1. The card's first-boot configuration chooses `deevnet` or `non-deevnet`

**One generic image stays.** The choice is made on the card, at first boot, with `deevnet` the
default.

| | `deevnet` (default) | `non-deevnet` |
|---|---|---|
| Server certificate | from the Tenant Service CA, for the tenant's site-less names and its site names (ADR-0040) | from the owner's own issuing CA, once set up |
| Device certificates | from the Tenant Device CA, at the Mobile Factory | from the owner's own issuing CA |
| Computers and devices trust | the Deevnet Root | the owner's root |
| Renewal | each year, at a visit or by a request that travels | the owner's, on the Pi |
| The starter kit | on the card, unused | the owner's to run |

### 2. A Deevnet Pi holds certificates, never a CA key

**At provisioning, the kit makes the server key and a request; the Mobile Factory signs it in a work
session; the kit installs the certificate and its chain.** Renewal is the same three steps. A
request and a certificate are public and may travel on a USB stick; the tenant's token, which
authorizes, stays with the owner.

**Devices dial a name and the Pi's address, and verify the name.** mbedTLS sets the expected name
apart from the address, and ESP-MQTT and MicroPython expose it. The Pi's own services dial its
names too, mapped to loopback on the Pi, so its certificate needs neither `localhost` nor an
address.

**A Deevnet Pi's certificate never carries the bus name** (ADR-0040 §5).

**Off Deevnet, the certificate stops serving people first.** At the owner's house a browser reaches
the Pi by its `.local` name or address, which the certificate does not name, unless the owner
trusts the Deevnet Root and resolves the Pi's Deevnet names locally. Devices keep working until it
expires, a year at most, because they verify a name and trust the Deevnet Root. That year is the
owner's time to move to a PKI of their own.

### 3. The starter kit makes a two-tier PKI

**Every image carries the ceremony tools, given parameters for the owner's names**, and
`deevnet-kit pki init` walks a `non-deevnet` owner through them:
1. the owner's organization name, for the CA subjects;
2. the names the Pi answers to: its `.local` name, the owner's domain if any, its addresses;
3. a USB stick for the root key, encrypted as the ceremony's key media are.

**It then makes the owner's root on the stick and an issuing CA on the Pi**, issues and installs the
Pi's server certificate, exports the root for computers and devices, and shows how to enroll a
device.

**The root never sits on the Pi.** A failed or stolen card costs the issuing CA: the owner signs a
new one from the stick, and nothing their devices trust changes. Renewal and enrollment need only
the Pi.

**It is a starter kit**, with instructions on how to take it further. Deevnet holds nothing of it and
trusts none of it.

**Until the owner runs it, a `non-deevnet` card keeps today's first-boot certificate as a
placeholder.**

### 4. Leaving Deevnet is a trust transition, in order

1. The owner's root reaches every device and computer **beside** the Deevnet Root.
2. The Pi's certificates are reissued by the owner's issuing CA.
3. Once every device is known to hold the owner's root, the Deevnet Root is removed from them.

**The service stays up throughout. Deevnet's keys are never handed over**: independence is a new
authority. A device that takes an anchor only by cable is provisioned again at step 1, which is its
application's to plan (ADR-0011).

---

## Consequences

**Every Pi starts as a Deevnet Pi**, and an owner who leaves has the tools to do it.

**The ceremony tools gain parameters** (organization, names, constraints) and a step that issues
leaves, server and device.

**`deevnet-kit` grows** a first-boot `deevnet` / `non-deevnet` setting, a request-and-install path
for Deevnet certificates, and `pki init`. Its first-boot CA becomes the `non-deevnet` placeholder.

**On the operator's own Deevnet Pis the tools sit unused**, or are removed as a step of deploying the
Pi to production. They hold no key.

---

## Alternatives considered

- **Withdrawn: three modes on the card** (`deevnet`, `own` as the generic default, `bring`). `own`
  recorded what the kit already did rather than a choice. `bring` served an owner with a PKI of their
  own, who needs no starter kit.
- **Rejected: a single CA on the card for `non-deevnet`.** Losing the card would re-anchor every
  device.
- **Rejected: two images, with and without the tools.** Two artifacts to build and publish for a few
  kilobytes of scripts, and a Deevnet Pi could not leave without a new card.
- **Rejected: a Deevnet Pi holds a tenant CA.** A CA key on field hardware.

---

## Open questions

None.

---

## What would settle it

V7, V8 and V11 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan).
