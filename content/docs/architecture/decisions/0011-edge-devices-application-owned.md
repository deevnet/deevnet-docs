---
title: "ADR-0011: Edge Devices Are Application-Owned and Platform-Attached"
weight: 11
---

# ADR-0011: Edge Devices Are Application-Owned and Platform-Attached

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-13 |
| **Scope** | Who owns a physical device an application uses, what the platform knows about it, which network it joins, and how it reaches the services it needs |
| **Depends on** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) |
| **Related** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/), [ADR-0003: Tenant Egress on a Single-Member Fabric](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/), [ADR-0009: Network Device Configuration Is Inventory-Owned and Controller-Applied](/docs/architecture/decisions/0009-network-device-config-ownership/) |

---

## Context

Physical microcontrollers have been treated as substrate IoT devices. The treatment conflated
concerns that answer to different owners:

1. **Ownership.** Who owns the device's purpose, its firmware and its keys?
2. **Attachment.** Which network does it join, and over what?
3. **Tooling.** What does the platform provide to build its firmware?

A fourth concern was hiding inside the second:

4. **Trust.** How much is a device on that network trusted?

### What exists

**EdS.** An LP jacket stand drives an RGB strip from album cover art.
- The stand is an ESP32 on the IoT segment. `lightd`, which publishes its scenes, runs in the `eds`
  tenant.
- The broker between them, `dv02mqt001v01`, sits on IoT Backend and *"belongs to neither"*
  (`ansible-inventory-deevnet` commit `d8c31cd`). It is there because MQTT clients dial the broker
  and the tenant fabric has no inbound path.
- The EdS repository holds all three halves:
  - the firmware (`firmware/lp-stand`)
  - the services
  - the tenant Terraform (`infra/deevnet-tenant-eds`, not yet applied)
- The firmware has a broker URI, username and password compiled in through `menuconfig`.
- TLS is optional, with the CA embedded at build time.
- There are two OTA slots. No secure boot or flash encryption is configured.
- The broker listens in plaintext on 1883.

**Ma Bell.** A Bluetooth gateway for vintage telephones.
- Its ESP32 is a substrate host, `dv02bgw001e01`, in the `edge_devices` group under
  `infrastructure`, with a DHCP reservation and CNAMEs.
- Its Wi-Fi credentials are written into NVS over USB by a provisioning script and can't be changed
  from the running device.

**Pumpkin.** An ESP32 with no networking at all, and no tenant. It is an application with a device
and nothing to attach.

### The ownership test

> *Would this device have a reason to exist if its application disappeared?*

- A switch, an AP, a hypervisor or the Builder would. They serve whatever runs on the site.
- The LP stand, the Ma Bell gateway and the pumpkin would not.

The test separates **owning a device's purpose** from **providing the infrastructure it uses**.
Deevnet currently merges the two.

### What the network allows

- **Tenant networks are virtual.**
  [ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) rejected core-router VLANs
  per tenant (Option A) and the VLAN-aware bridge ("the starter trap").
  [Network Segmentation](/docs/standards/network-segmentation/) §4 states: *a tenant MUST NOT
  require a VLAN, a switch change, or a core router change to create.*
- **Proxmox connects EVPN only at Layer 3.** The SDN documentation describes exit nodes as the way
  between an EVPN network and the real network. It documents no way to put a physical VLAN into an
  EVPN VNet, and automatic DHCP exists only in Simple zones
  ([pve-docs, SDN](https://pve.proxmox.com/pve-docs/chapter-pvesdn.html)).
- **The fabric is one hypervisor with one NIC**
  ([Limits](/docs/architecture/limits/)).
- **Tenants have no inbound path.**
  [ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/) built egress
  only.
- **The IoT segment is a trust class, not a device label.**
  [Network Segmentation](/docs/standards/network-segmentation/) rates IoT as *medium trust — devices
  run controlled firmware*, and IoT Vendor as a strict containment zone where *devices are assumed
  compromised*.

---

## Options considered

### A — Devices are substrate-owned

Today's model. The substrate records, names, addresses and credentials each device, and holds its
broker permissions.

- **Pros:** it works today, and everything is in one inventory.
- **Cons:**
  - The substrate holds application device records, credentials and topic permissions.
  - Every new device is a substrate commit, which fails the
    [ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/) test.
  - Its only answer for an application with no tenant is "then it is substrate."

### B — Devices join their tenant's network

Each tenant gets an edge VLAN, carried over the AP trunk. Devices reach it by a per-tenant SSID, or
by one shared SSID whose private pre-shared keys (PPSK) map each key to a tenant VLAN. The VLAN is
bridged or routed into the tenant's VRF.

- **Pros:** tenant isolation extends to the tenant's devices, and "tenant" becomes one abstraction
  for everything an application owns.
- **Cons:**
  - It reverses ADR-0001's rejection of Option A, and breaks the §4 MUST NOT.
  - Every tenant needs edits to two switch trunks (the AP port and the hypervisor port), a
    controller network, an SSID or PPSK entry, and node-local bridge state that SDN does not manage.
  - There is no documented Proxmox path into an EVPN VNet, and no DHCP there.
  - Devices inside a tenant are unreachable from management for diagnosis or recovery.
  - PPSK is WPA/WPA2 only.
  - Its keys would live in the controller's database, which ADR-0009 calls derived state.
  - With a single stored list of keys, a bad reconcile takes every device off the network at once.
    Each NVS-provisioned device then needs a USB visit.
- **Verdict:** Rejected.

### C — Devices are application-owned and platform-attached

The application owns the device. The platform attaches it to the access network of its trust class
and serves it through scoped platform services.

- **Pros:**
  - It needs nothing ADR-0001 forbids.
  - It fits ADR-0010.
  - It covers tenants and tenantless applications alike.
  - The IoT segment stays what the standard says it is.
- **Cons:**
  - Devices of different owners share a Layer 2 domain, so isolation between them depends on the
    services and the AP rather than on the network.
  - Parts of it depend on mechanisms that don't exist yet (see Open questions).

---

## Decision

**Option C.**

### 1. Four axes, four owners

| Axis | Owned by | What it covers |
|---|---|---|
| **Ownership** | The application, which may or may not be a tenant | Firmware source, build configuration, release artifacts, signing keys, device secrets, behaviour |
| **Identity** | The platform | Only what it must know to attach, authenticate and account for a device |
| **Attachment** | The substrate, chosen by **trust class** | The access segment (IoT or IoT Vendor), over Wi-Fi or a switch port |
| **Access** | Platform services, scoped per owner | Rendezvous services on IoT Backend, such as the broker; per-device permissions |

### 2. Tenants own devices; they do not contain them

The tenant fabric stays what ADR-0001 built: isolated virtual compute. A device a tenant owns joins
the access network of its trust class and reaches the tenant through platform services, as the LP
stand already does.

### 3. Attachment is by trust class, not by owner

- A device with controlled firmware whose owner is known joins **IoT**.
- A device whose firmware its vendor controls joins **IoT Vendor**.

Owners are kept apart above Layer 3, by per-device credentials and per-owner scopes in the services.
Isolation between clients on the AP is added where the equipment can provide it (Open question 4).

### 4. The platform keeps identity; the owner keeps everything else

- **Device secrets and signing keys never enter the substrate vault.**
- Firmware is built and released by its owner, from its owner's repository.

### 5. "Edge device" is a first-class concept

An **edge device** is:
- physical
- application-owned
- platform-attached
- outside the tenant fabric

Its lifecycle belongs to its owner. Its attachment belongs to the platform. It is registered the
way ADR-0010 prescribes: the platform issues the owner a scope once, and the owner registers
devices within it.

### 6. Tooling is a capability, not a claim of ownership

The Builder may provide a firmware toolchain, as it already provides Terraform, Packer, Go and Node.

- **Version authority belongs to the project.** A firmware repository pins its toolchain, for
  example the image tag `espressif/idf:vX.Y.Z`, just as a tenant pins its module tag.
- **Offline staging reuses what exists.** The artifacts role already stages podman images as
  tarballs, so an offline copy needs no new mechanism.
- **The Builder never holds signing keys.**

The air-gap scope already excludes edge devices ([Correctness](/docs/standards/correctness/)). This
record doesn't change that.

---

## Open questions

These must be answered before this record is accepted.

1. **How does an owner register devices within its scope?**
   - Mosquitto's dynamic security plugin changes clients and permissions at runtime, but can't
     confine an administrator to a topic prefix.
   - Candidates:
     - a small platform registration service in front of it
     - a broker with native tenant namespaces
     - a certificate authority issued per owner, with mutual TLS and permissions keyed to the
       certificate name. *Unverified: that a name prefix can be bound to the issuing authority.*
2. **Does an owner's device still need a substrate host record?**
   - [Naming](/docs/standards/naming/) defines a host by a deterministic MAC-to-IP mapping, and
     `dv02bgw001e01` has a DHCP reservation, an A record and CNAMEs.
   - A device identified by its credential rather than its address could lease from the IoT pool
     and be named in its owner's own zone under ADR-0004.
3. **Shared or per-device Wi-Fi keys?**
   - A shared key per segment means one lost device exposes the key for every device on it, and
     rotation means a USB visit to every NVS-provisioned device.
   - Per-device PPSK keys, all mapped to the segment's own VLAN, give per-device revocation without
     per-tenant VLANs. They are WPA2-only.
   - PPSK profile endpoints appear in TP-Link's published Open API specification, but coverage on
     the site's controller (6.3.0.45) is unverified, and ADR-0009 requires the documented API.
4. **How are clients isolated on the IoT SSID?**
   - Omada's per-SSID isolation is its Guest Network setting, which also blocks all private address
     ranges ([Omada](https://support.omadanetworks.com/us/document/12928/)). It can't be used for
     devices that must reach a broker.
   - The vendor's alternative is EAP ACLs. To be verified against the controller.
5. **Two questions for records of their own**, numbered when opened:
   - **How a device reaches a service a tenant exposes directly.** This is tenant ingress, which
     ADR-0003 does not provide.
   - **The firmware supply chain:**
     - custody of signing keys. ESP32 Secure Boot v2 stores one public key per chip, permanently
       ([Espressif](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/security/secure-boot-v2.html)),
       so whoever holds the key owns every future image for that chip.
     - where OTA images are hosted so the IoT segment can reach them
     - keeping secrets out of firmware binaries
     - recovery once flash encryption blocks USB reflashing

---

## Consequences

**The broker's device records move to their owner, once Open question 1 has an answer.** Until then
`lp-stand-01` stays in `mqtt_acls` and `vault_mqtt_users` as recorded ADR-0010 debt.

**`edge_devices` needs a new home or a new meaning.** A group of application-owned devices can't
stay under `infrastructure`. Where it goes depends on Open question 2.

**Isolation now leans on enforcement the site doesn't yet have.** Owners share the IoT segment, so
the segment's zone policy must actually be in force. It is not:
[INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/) records that the zone policy has
never been applied, and [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) is where that
is planned. This record raises that change's priority; it does not replace it.

**Applications that need nothing from the platform owe it nothing.** A device with no network, like
the pumpkin, is not enrolled anywhere.

**Descriptive pages change only on acceptance.** The tenant segments and IoT inhabitants in
[Network Segmentation](/docs/architecture/network-segmentation/), the Raspberry Pi row in Tenant
Compute, and the tenant contract are left as they are while this record is Proposed.

---

## Current state

- **Proposed.** Nothing is implemented.
- The LP stand, the Ma Bell gateway and the MQTT broker remain exactly as `d8c31cd` and earlier
  commits left them.
