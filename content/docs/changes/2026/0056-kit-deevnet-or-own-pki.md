---
title: "CHG-0056: A Deevnet Pi by Default, With a Starter PKI Kit"
weight: -56
---

# CHG-0056: A Deevnet Pi by Default, With a Starter PKI Kit

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. After [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/) (site-less names to issue); one `deevnet-kit` release, one image build, the image staged to the tenant downloads |
| **Site** | mobile |
| **Systems** | `deevnet-kit`; the take-home image `raspios-bookworm-mobile-pi-backend.img.xz`; the tenant downloads on `dv02obs001v01`; one Pi of the Pi lab for the test |
| **Automation** | `deevnet-provisioning-api` (`cmd/deevnet-kit`), `deevnet-image-factory` `make pi-backend`, `deevnet.mgmt` `scripts/pki/` |
| **Risk** | Medium. Most likely to go wrong: a card that sets nothing changes behavior on upgrade. `deevnet` is the default and keeps today's first boot until a certificate is installed |
| **Related changes** | [CHG-0050](/docs/changes/2026/0050-kit-extra-names/), [CHG-0051](/docs/changes/2026/0051-pi-backend-on-kit-0-12/) (the image this replaces), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) |
| **Related incidents** | None |
| **Related runbooks** | [Pi Lab](/docs/runbook/tenant/pi-lab/) |

---

## Summary

A take-home Pi makes its own CA at first boot today, and its certificates are trusted by nothing.
[ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/) makes it a
Deevnet Pi by default: its server certificate is signed by the Tenant Service CA from a request it
makes, and its devices' certificates by the Tenant Device CA. A `non-deevnet` card instead gets a
starter kit, `deevnet-kit pki init`, that walks its owner through a two-tier PKI of their own: the
root on an encrypted USB stick, an issuing CA on the Pi
([review](/docs/architecture/reviews/2026-10-tenant-pki/), phase P7).

## Goal

- The card's first-boot configuration takes `pki=deevnet` (the default) or `pki=non-deevnet`.
- `deevnet-kit` makes a server key and a request, writes the request where it can be carried, and
  installs a certificate and its chain from a work session. The same three steps renew it.
- A Deevnet Pi's own services dial its names, mapped to loopback; its certificate carries neither
  `localhost`, an address nor the bus name.
- The ceremony tools take parameters for an owner's names, and issue a leaf.
- Every image carries them. `deevnet-kit pki init` asks for the owner's organization, the Pi's
  names and a USB stick, makes the root on the stick and an issuing CA on the Pi, installs the Pi's
  certificate and exports the root.
- A `non-deevnet` card keeps today's first-boot certificate until `pki init` runs.

## Scope

**In scope:** `deevnet-kit` (the switch, request and install, `pki init`), the ceremony tools'
parameters and leaf step, the image, the downloads, the Pi Lab pages.
**Out of scope:** the Mobile Factory's signing of a Pi's request beyond what CHG-0054 issues;
removing the tools from the operator's own Pis, which is a post-deploy task of each.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| An existing card changes behavior | take-home Pis | `deevnet` keeps today's first boot until a certificate is installed |
| The owner's root key left on the Pi | `non-deevnet` Pis | `pki init` writes it only to the stick, and refuses an unencrypted one |
| The ceremony tools changed for Deevnet's own ceremonies | `scripts/pki/` | Deevnet's names stay the defaults; a ceremony run with no parameters is unchanged |

## Prerequisites

- [ ] CHG-0054 complete
- [ ] One Pi of the Pi lab and a USB stick for the test

## Procedure

### Step 1: The ceremony tools

Parameters for names, and a leaf step.

**Verify:** a ceremony run with no parameters produces the same subjects and constraints as before.

### Step 2: `deevnet-kit`

The switch, request and install, `pki init`.

**Verify:** V7 and V11 against the test Pi.

### Step 3: The image

Build with `make pi-backend`, stage to the downloads.

**Verify:** a new card boots as `deevnet` with today's behavior until a certificate is installed.

## Verification

V7, V8 and V11 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass.

## Undo

The previous image stays in the downloads until this one is verified.
