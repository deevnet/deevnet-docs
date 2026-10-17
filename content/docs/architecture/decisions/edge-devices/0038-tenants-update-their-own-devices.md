---
title: "ADR-0038: Tenants Update Their Own Devices"
weight: -38
---

# ADR-0038: Tenants Update Their Own Devices, Through Services They Already Have

|  |  |
|--|--|
| **Status** | Accepted (2026-10-17): already how the platform works. `eds` updates its three devices over the air through the broker, under its own ADR-0035, with no platform service of its own |
| **Date** | 2026-10-17 |
| **Scope** | How new firmware reaches a tenant's edge device once the device is in place, and where the image is kept. Not how the firmware is built or signed ([ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) §4, unchanged), and not how a device reaches a tenant's service in general ([ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/), unchanged). |
| **Extends** | [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/): answers the hosting bullet of open question 6, *"where OTA images are hosted so the IoT segment can reach them"*. The question's other bullets stay open. |
| **Amends** | [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §3: *"firmware release hosting"* and *"OTA"* leave its list of later platform layers. *"Jobs"* stays. |
| **Related** | [ADR-0032](/docs/architecture/decisions/edge-devices/0032-every-device-belongs-to-a-tenant/) (every device belongs to a tenant), [ADR-0034](/docs/architecture/decisions/tenant-model/0034-tenants-deliver-their-own-code/) (the same rule for workloads) |

---

## Context

**Firmware is already the owner's.** ADR-0011 §4 has firmware built and released by its owner,
from its owner's repository, and keeps signing keys out of the substrate vault. ADR-0032 makes that
owner always a tenant.

**Two records still left room for a platform OTA service.** ADR-0011's open question 6 asks where
OTA images are hosted so the IoT segment can reach them. ADR-0012 §3 lists *"firmware release
hosting"* and *"OTA and jobs"* among the later layers of the platform, each to have its own record.

**A tenant has done it without either.** `eds` (its ADR-0035, 2026-10-16) sends a build to one
device through the broker the device already uses, in pieces on topics the device's account is
granted in the tenant's Terraform, from a sender on the tenant's own workload with a broker account
of its own. The device writes the image to its spare slot and keeps it only once it has reached the
broker again. Nothing was hosted, and the platform's only part was the grants. On 2026-10-17 each of
its three devices was updated this way, one undid a bad build by itself, and one refused an image
that was not its own.

**This site is a mobile IoT lab, not production.** Its devices are few, each with an owner who is
present.

---

## Decision

### 1. A device's firmware updates are its tenant's

- **The tenant decides how a build reaches its devices, and carries it out.** Which mechanism,
  how often, how a bad build is undone and who may send one are the tenant's, recorded in the
  tenant's repository.
- **The substrate never delivers device firmware.** It attaches the device and issues what the
  device needs to reach the platform's services (ADR-0011 §4); what runs on it is the tenant's.

### 2. The tenant uses services it already has

- **An update rides on what the device already reaches.** The broker, with topics granted to the
  device and to a sender in the tenant's Terraform, is enough, as `eds` shows. A device service
  the tenant exposes under ADR-0020 is another.
- **No new network path is opened for updates.** A tenant that wants a device to download its
  image from a server makes that server reachable the way ADR-0020 already allows, not by asking
  for an inbound path into its network.

### 3. The platform hosts no firmware and runs no OTA service

There is no image store for devices, no update scheduler and no agent. The platform's part in an
update is the same as in any other message: the broker, the grants and the device's credentials.

---

## Consequences

**The platform stays a host.** It carries a tenant's update as it carries any message, and has no
release, rollout or rollback of its own to keep working.

**Each tenant builds its own updater.** `eds` wrote a receiver into its firmware and a sender for
its workload. Another tenant writes its own, or copies one; the platform offers none to share.

**What may send a build is a grant.** A tenant's broker account that may publish to a device's update
topics can run code on that device. Keeping that account narrow, and its password safe, is the
tenant's, as with any credential it is issued. Signed images, which would make the password alone
not enough, are part of the supply chain ADR-0011 still leaves open.

**An update must not need what the device cannot reach.** A tenant that hosts images for its devices
is bound by ADR-0020 like any other device-facing service.

---

## Alternatives considered

- **A platform image store on IoT Backend, from which devices download.** Not pursued: it puts every
  tenant's releases in the platform's custody, and a service to run, to save each tenant a receiver.
  ADR-0011 already keeps firmware the owner's.
- **A platform OTA service that schedules and rolls out builds.** Rejected: rollout policy belongs to
  the firmware's owner, and the platform would need to know each device's firmware to do it.
- **Leaving it to a later record, as ADR-0012 §3 did.** Not pursued: a tenant has answered it, and an
  open layer invites building one.

---

## Current state

- **Accepted, and in use.** `eds` updates `lp-stand-01`, `cover-screen-01` and
  `turntable-power-01` through the broker, with grants declared in its tenant Terraform and applied
  2026-10-16.
- ADR-0011's open question 6 stays open for its other bullets: custody of signing keys, keeping
  secrets out of binaries, and recovery once flash encryption blocks USB reflashing.
