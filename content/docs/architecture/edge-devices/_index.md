---
title: "Edge Devices"
weight: 4
bookCollapseSection: true
---

# Edge Device Architecture

An **edge device** is a physical thing an application owns and the platform attaches to the
network — a microcontroller driving lights, a gateway bridging an old telephone, a sensor. It is
the third category of thing in a Deevnet site, alongside the substrate that provides the
infrastructure and the tenants that run virtual workloads on it.

It is a category of its own because it does not fit either of the others. A device is **physical**,
so it is not a tenant workload. It is **owned by an application**, so it is not substrate. It runs
on the access network rather than in the tenant fabric, and it is accountable to whoever wrote its
firmware rather than to whoever runs the site.

---

## The ownership test

[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) settles what makes
something an edge device with one question:

> **Would this device have a reason to exist if its application disappeared?**

A switch, an access point, a hypervisor or the builder would — they serve whatever runs on the
site, and they are substrate. An LP jacket stand that lights up to match album art would not. Nor
would a gateway that exists only to make one old telephone work. Those are edge devices.

The test separates **owning a device's purpose** from **providing the infrastructure it uses**.

---

## Four axes, four owners

The concept only works because four separate questions are kept separate. Conflating any two of
them is how a device ends up either inside a tenant's network or inside the substrate's inventory,
and both are wrong.

| Axis | Owned by | What it covers |
|------|----------|----------------|
| **Ownership** | The application, which may or may not be a tenant | Firmware source, build configuration, release artifacts, signing keys, device secrets, behaviour |
| **Identity** | The platform | Only what it must know to attach, authenticate and account for a device |
| **Attachment** | The substrate, chosen by **trust class** | The access segment, over Wi-Fi or a switch port |
| **Access** | Platform services, scoped per owner | Rendezvous services the device and the application both reach; per-device permissions |

Two consequences follow, and they are the load-bearing ideas on this page:

**Ownership is not network placement.** A device an application owns does not join that
application's network. An EdS device is not a member of the EdS tenant overlay, is not addressed
from it, and is not Layer 2 adjacent to it. Tenants own devices; they do not contain them.

**Attachment is not authorization.** Joining the wireless network establishes only that a device is
permitted onto an access segment. It says nothing about which services it may consume. A device
that has associated successfully has been *attached*, not *authorized*.

---

## Attachment is by trust class

A device joins the access segment matching **how much its firmware is trusted**, never the segment
of whoever owns it.

| Trust class | Firmware controlled by | Segment | What it may reach |
|---|---|---|---|
| **IoT** | A known owner, who is accountable for it | IoT | Device-facing platform services, and controlled outbound internet |
| **IoT Vendor** | The vendor, and assumed compromised | IoT Vendor | Outbound internet only — full containment from every internal segment |

This is why creating a tenant never creates a VLAN. Devices of many owners share one segment, and
the number of access segments is a function of how many *trust levels* exist, not how many
applications do.

The alternative — a segment per owner — was considered and rejected twice, and both records are
worth reading before proposing it again:
[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) Option B, and
[ADR-0019](/docs/architecture/decisions/0019-tenant-l2-at-the-access-edge/), which re-examined it
against a variation that removed its worst cost and still found it wanting.

---

## What the platform keeps, and what it does not

The platform knows only what it must to attach and account for a device:

- **It issues the credential that gets a device onto the network.** Today that is a wireless key,
  issued per tenant per trust class rather than per device
  ([ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §3).
- **It never holds device secrets or signing keys.** Those stay with the application that owns the
  device. Whoever holds a signing key owns every future image for that chip, and that is not a
  thing the substrate should be able to do.
- **It never builds the firmware.** The builder may offer a toolchain the way it offers Terraform
  or Go, but offering a tool is not a claim of ownership, and the project pins its own versions.
- **A device needs no substrate host record.** Its identity is its credential, not its address
  ([ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) open question 2).

---

## Applications without tenants

An application that owns devices need not be a tenant at all. The pumpkin runs no workload and has
no network; the Ma Bell gateway has a device but no VMs. The model covers them because ownership is
an application-level fact, not a tenancy-level one — which is precisely what the old "if it isn't a
tenant it must be substrate" framing could not do.

---

## Child documents

- [Access](/docs/architecture/edge-devices/access/) — how a device reaches the services its
  application exposes, and the boundary that decides what it may consume

---

## Current state

The model is decided and largely built. Wireless attachment is real: `DVNTM-IOT` is a PPSK network
on the IoT segment, and a tenant issues its own key through the Deevnet API without a substrate
commit.

The other side of attachment is built too. The broker is deployed and serving TLS
([CHG-0015](/docs/changes/2026/0015-vernemq-broker/)), the device registry answers rather than `501`
([CHG-0014](/docs/changes/2026/0014-tenant-device-registry/)), and a tenant can be issued an MQTT
account scoped to its own topic prefix ([CHG-0016](/docs/changes/2026/0016-broker-accounts/)) — a
real client used one to connect over TLS, publish inside its prefix, and be denied outside it.

**"Attachment by trust class" is now a control rather than an intention.** The zone policy is
applied and enforcing ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)), demonstrated
from a real client on the IoT segment and, for IoT Vendor, against a live phone that could reach
nothing internal. Four items in that change are recorded as untested rather than passed, so read its
verification before relying on a specific flow.

What no record yet shows is a device and its application meeting on the rendezvous end to end. Every
piece is in place and both sides can hold accounts on it; nothing has been stood up on the
application side to consume what a device would publish.
