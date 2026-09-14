---
title: "ADR-0011: Edge Devices Are Application-Owned and Platform-Attached"
weight: 11
---

# ADR-0011: Edge Devices Are Application-Owned and Platform-Attached

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-13 |
| **Validated** | 2026-09-14, read-only, before acceptance. See [Validation](#validation-2026-09-14) |
| **Scope** | Who owns a physical device an application uses, what the platform knows about it, which network it joins, and how it reaches the services it needs |
| **Depends on** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) |
| **Related** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/), [ADR-0003: Tenant Egress on a Single-Member Fabric](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/), [ADR-0009: Network Device Configuration Is Inventory-Owned and Controller-Applied](/docs/architecture/decisions/0009-network-device-config-ownership/), [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/) |

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
- **The IoT segment is not enforced today.** The validation on 2026-09-14 found the core router
  passing all traffic between every segment
  ([Validation → The core router](#the-core-router-enforces-no-segment-boundary)).

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
  - PPSK is WPA/WPA2 only. *As validated on 2026-09-14, none of the sources checked states which WPA
    versions PPSK supports ([Open question 3](#open-questions)). This remains unconfirmed.*
  - Its keys would live in the controller's database, which ADR-0009 calls derived state.
  - With a single stored list of keys, a bad reconcile takes every device off the network at once.
    Each NVS-provisioned device then needs a USB visit.
- **Verdict:** Rejected.
- **Validation note (2026-09-14).** The wireless half of this option *is* available. The site's
  controller documents a VLAN per PPSK key, and the vendor's PPSK guide describes the client
  joining that key's VLAN ([Validation](#wireless-per-key-vlans-ppsk)). The option stays rejected
  for the reasons above, all of which are on the network and fabric side. Nothing found on
  2026-09-14 changes them.

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

These must be answered before this record is accepted. Each carries what the 2026-09-14 validation
found. The evidence and its sources are in [Validation](#validation-2026-09-14).

1. **How does an owner register devices within its scope?**
   - Mosquitto's dynamic security plugin changes clients and permissions at runtime, but can't
     confine an administrator to a topic prefix.
   - Candidates:
     - a small platform registration service in front of it
     - a broker with native tenant namespaces
     - a certificate authority issued per owner, with mutual TLS and permissions keyed to the
       certificate name. *Unverified: that a name prefix can be bound to the issuing authority.*
   - **Found 2026-09-14:** none of these could be tried against the running broker, because it isn't
     running where inventory says. `dv02mqt001v01` isn't in DNS, doesn't answer ping, and has
     1883, 8883 and 22 closed, while the core router passes everything. The question is still open,
     and a broker has to be up before any candidate can be tested
     ([The broker](#the-broker-is-not-reachable)).
   - **Proposed answer:** [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/). Owners
     register devices through a Deevnet API and Terraform provider that confine them to their own
     topic prefix. The broker behind it is ADR-0012's own open question.
2. **Does an owner's device still need a substrate host record?**
   - [Naming](/docs/standards/naming/) defines a host by a deterministic MAC-to-IP mapping, and
     `dv02bgw001e01` has a DHCP reservation, an A record and CNAMEs.
   - A device identified by its credential rather than its address could lease from the IoT pool
     and be named in its owner's own zone under ADR-0004.
   - **Found 2026-09-14:** no new evidence. Nothing tested bears on it.
3. **Shared or per-device Wi-Fi keys?**
   - A shared key per segment means one lost device exposes the key for every device on it, and
     rotation means a USB visit to every NVS-provisioned device.
   - Per-device PPSK keys, all mapped to the segment's own VLAN, give per-device revocation without
     per-tenant VLANs. They are WPA2-only. *(Unconfirmed as of 2026-09-14; see below.)*
   - PPSK profile endpoints appear in TP-Link's published Open API specification, but coverage on
     the site's controller (6.3.0.45) is unverified, and ADR-0009 requires the documented API.
   - **Found 2026-09-14:**
     - **Controller: supported, in the documented API.** The spec the site's controller serves lists
       PPSK profile create, modify, delete, and add or remove individual keys. Each key can carry its
       own VLAN and an optional MAC binding. This meets ADR-0009's "documented" requirement.
     - **AP model and firmware: supported per a vendor list, not tested.** TP-Link's PPSK support
       table lists the EAP650-Outdoor(US) v1, the site's AP, as supporting PPSK without RADIUS from
       firmware 1.0.4. That is the firmware the AP runs now.
     - **Not tested on the AP.** The reasons are under
       [What was not tested](#what-was-not-tested-and-why).
     - **WPA2-only is unconfirmed.** Neither the vendor's PPSK guide nor the API spec states a WPA
       version for PPSK. The spec asks for a WPA version only for plain WPA-Personal. The claim
       above is kept, but marked, until a device test or vendor document settles it.
     - **Implication for ADR-0010 (analysis, not tested).** Every PPSK write needs the same
       controller permission as creating SSIDs and ACLs. A credential that can add a device's key
       can therefore change the whole site's wireless configuration. So per-device keys can't be
       handed to an owner as self-service. They would have to be issued by a platform service in
       front of the controller, or by the substrate, which is a recurring substrate act. Whether a
       custom controller role can narrow this wasn't checked.
   - **Proposed answer:** [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/).
     Per-device keys are issued through the Deevnet API, which holds the controller credential and
     always binds a key to the device's trust-class VLAN.
4. **How are clients isolated on the IoT SSID?**
   - Omada's per-SSID isolation is its Guest Network setting, which also blocks all private address
     ranges ([Omada](https://support.omadanetworks.com/us/document/12928/)). It can't be used for
     devices that must reach a broker.
   - The vendor's alternative is EAP ACLs. To be verified against the controller.
   - **Found 2026-09-14:**
     - **There is no other isolation switch.** The controller's SSID schema has no client-isolation
       field. The only per-SSID setting that separates clients is Guest Network.
     - **ACLs alone can't isolate clients from each other.** The vendor states that access control
       *"can't take effect to wireless clients which connected with the same SSID of same AP."*
     - **Guest Network plus an EAP ACL permit is a documented combination.** A TP-Link staff guide
       puts guests on Guest Network and adds an EAP ACL rule permitting them to reach one private
       host. Applied here, the IoT SSID would run as a Guest Network, which isolates clients, with a
       permit rule for the broker. The controller's documented API has EAP ACL create, with an SSID
       or network as the source and an IP or IP-and-port group as the destination.
     - **What the guide doesn't say, so it is not assumed:**
       - whether clients stay isolated from each other once the permit rule exists
       - whether the zone's own gateway (DNS, DHCP) needs a permit too
       - which controller and firmware versions it applies to
     - **So the earlier line "It can't be used for devices that must reach a broker" is likely too
       strong.** Guest Network *alone* can't, but with an ACL permit it may. The device test settles
       it.
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

## Validation (2026-09-14)

This was a pre-acceptance check of the assumptions above, run from the control host
`dv00bld001p01` on the management segment. **Nothing on any device was changed:**
- unauthenticated GETs to the Omada controller
- read-only API calls to the core router
- TCP and ICMP probes

Vendor statements are quoted as written. Anything inferred is labelled.

### Wireless: per-key VLANs (PPSK)

**The site's controller.** The controller reports `controllerVer 6.3.0.45`. Its served Open API
specification (`/v3/api-docs/00 All`, 1,856 paths) documents:

| Capability | Operations | What the spec says |
|---|---|---|
| PPSK profiles | `createPPSKProfile`, `createPPSKProfileV2`, `modifyPPSKProfile`, `deletePPSKProfile`, `getPPSKProfiles` | Profile holds a list of keys |
| Per-device keys | `addPSKsToPPSKProfile`, `deletePSKsToPPSKProfile` | Keys added or removed one by one, without rewriting the profile |
| VLAN per key | `ppsk[].vlan` | *"Vlan Bound With PSK, should be within the range of 1-4094."* |
| MAC per key | `ppsk[].mac` | *"Mac Bound With PSK."* |
| Bulk keys across a VLAN range | `generate-psk`, `vlanPool` | *"PSK Bound Vlan range, should be like: 10-1000."* |
| PPSK SSID | `createSsidV2` `security` | *"4: PPSK without RADIUS; 5: PPSK with RADIUS"*, with `ppskSetting.ppskProfileId` |
| RADIUS-assigned VLAN | RADIUS profile `wirelessVlanAssignment`; built-in RADIUS user `type` 1 (MAC auth) with `vlanId` | *"VLAN assignment for wireless network enable status"* |
| Several VLANs on one SSID | `vlanSetting.customConfig` | *"If a device does not support multiple VLANs, the smallest VLAN you configured will be applied to the SSID."* |

Every PPSK write operation lists the same required permission as SSID and ACL creation:
*"Site Settings Manager Modify | Network Config Page Modify."*

**The vendor's PPSK guide.** From
[PPSK Configuration Guide](https://support.omadanetworks.com/my/document/13106/), last updated
12-20-2025: *"If you define the VLAN assignment, then the client will connect to the corresponding
VLAN after authentication."* The guide doesn't state supported models, firmware, WPA versions or a
key limit.

**The AP's model and firmware.** The AP is an EAP650-Outdoor(US) v1, per inventory and the
[Wireless AP runbook](/docs/runbook/recovery/console-recovery/wireless-ap/). It runs firmware 1.0.4
([CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/)). A TP-Link staff knowledge
article, [Getting To Know PPSK](https://community.tp-link.com/en/business/forum/topic/620762)
(2023-08-30, edited 2024-07-08), has this row in its table of *"original firmware version that
supports PPSK"*:

> EAP650-Outdoor（US） | 1.0 | EAP650-Outdoor(US)\_V1\_1.0.4 Build 20230421

It adds: *"The original and subsequent versions of the firmware in the list above all support PPSK
without RADIUS."*

This is a community knowledge article, not a support-site document. The AP's exact build number was
not read from the device.

### Wireless: client isolation

- **The controller API.** No SSID-level client-isolation field exists in the served spec. The only
  per-SSID separation setting is `guestNetEnable`. EAP ACLs (`createEapAcl`) take a source type of
  *"0: network; 1: IP Group; 2: IP-Port Group; 4: SSID"*, among others, and a destination of a
  network, IP group or IP-and-port group. There is no SSID destination.
- **Guest Network.**
  [How to Set Up Access Control to Create a Guest SSID](https://support.omadanetworks.com/us/document/12928/),
  last updated 08-12-2026:
  > All wireless devices connected to the SSID cannot communicate with each other; All wireless
  > devices connected to the SSID will be blocked from reaching any private IP subnet

  The same page:
  > Access Control function can't take effect to wireless clients which connected with the same
  > SSID of same AP.
- **Guest Network with an ACL exception.** From
  [How to allow guest network to access specific device on the main network by configuring EAP ACL?](https://community.tp-link.com/en/business/forum/topic/708978),
  by TP-Link staff, 2024-10-09, edited 2025-06-05:
  > Choose the Policy as Permit, Select the Source as the Guest SSID's Network, select the
  > Destination as the IP Group profile of the printer.

  It applies to *"All SDN EAPs"*. It doesn't state controller or firmware versions, or whether
  guest client-to-client isolation still holds with the permit in place.
- **A per-SSID isolation option.** A user asked for one outside Guest Network in
  [Client Isolation for Omada EAP](https://community.tp-link.com/en/business/forum/topic/728424)
  (2024-12-19). TP-Link staff replied by pointing to the EAP ACL guide above, not to an isolation
  setting.

### The core router enforces no segment boundary

These were read-only automation API reads of `dv02cor002p01`, which runs OPNsense 26.7.3.

- **Automation rules.** There are 25, and none is the declared zone policy:
  - `ansible:temp-allow-all-optN` passes `any` to `any` on each VLAN interface, and each rule
    exists **twice**. That covers Trusted, Storage, Platform, **IoT**, **IoT Vendor**, IoT Backend,
    **Guest**, management, blackhole and tenant transit.
  - Two of the pairs point at `opt11` and `opt12`, which are no longer assigned.
  - One `ansible:test-rule` sits on management.
- **Rules outside automation.** The router's rule listing also shows two rules that the automation
  API doesn't manage: *"temp: allow all VLAN 99"* on management, and a pass from `any` to
  `10.20.99.0` on Trusted. The `opnsense_firewall` role can't see or remove either.
- **Result: today every segment reaches every other.** IoT is not *medium trust*, and IoT Vendor is
  not a containment zone, in any sense the network enforces.

This also settles [INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/)'s open item
*"what the restore put back."* It adds two scope items to
[CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/):
- the two non-automation allow rules must be removed by hand
- the stale `opt11`/`opt12` and test rules must be removed

For the `opnsense_firewall` fixes CHG-0007 depends on, the router showed:
- **An omitted field becomes `any`.** The blank rule template defaults `protocol`, `source_net` and
  `destination_net` to `any`, and `ipprotocol` to `inet`. Existing rules read back as `any`, not
  empty, so the role's empty-string comparison is wrong.
- **VLAN clients get no automatic DHCP-server rule.** The only automatic DHCP rules are the client
  rules on WAN. Once the allow-all rules go, each zone's DHCP to its gateway, like its DNS, needs
  an explicit rule. *This was observed on the rule listing, not taken from vendor documentation.*

### The broker is not reachable

- **Deployment history.** `dv02mqt001v01`, IoT Backend, `10.20.35.20`, was recorded as created on
  `dv02hyp001p01` during the 2026-09-07 session (INC-0001). The `mosquitto` role exists in
  `ansible-collection-deevnet.mgmt` (`93e1952`).
- **On 2026-09-14:**
  - the name does not resolve at the core router
  - no ICMP reply
  - TCP 1883, 8883 and 22 all closed
- **Why this rules out the firewall.** The router passes all traffic between segments, so it can't
  be blocking the broker. The VM is down or gone, or `10.20.35.0/24` doesn't reach it.
- **Not checked.** Whether the VM exists on the hypervisor.

### What was not tested, and why

**PPSK, per-key VLANs, and Guest Network with an ACL permit were not tested on the AP.**
1. On this platform, PPSK and EAP ACLs are configured by the controller. The AP isn't adopted:
   it's *pending*, still on 1.0.4 ([CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/)).
2. The AP's standalone login is unknown and not in the vault. Adoption from the reset controller
   failed on it.
3. Every meaningful test creates configuration: a PPSK profile, an SSID and an ACL. This validation
   was deliberately read-only.
4. The vault holds no Open API client yet, so even authenticated *reads* of controller state
   weren't possible.

**The device test, to run after CHG-0005 adopts the AP.** Use a throwaway SSID, and don't touch
the four production SSIDs:
1. A PPSK profile with two keys, one bound to VLAN 30 and one to VLAN 31. Expect a client on each
   key to lease from `10.20.30.x` and `10.20.31.x` respectively. The AP is expected to support
   several VLANs; if it doesn't, both clients land in VLAN 30 (per the `vlanSetting` note).
2. The same SSID with Guest Network on, plus an EAP ACL permitting the broker's IP-and-port group.
   Expect:
   - two clients can't reach each other
   - both reach the broker
   - record whether the gateway's DNS and DHCP answer without their own permit
3. Record the WPA versions the controller offers for the PPSK SSID.
4. Remove the test SSID, profile and ACL.

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

The 2026-09-14 validation makes this concrete. The router is not merely missing the zone policy:
it runs explicit allow-all rules on every segment, including two that the automation can't see.
Trust-class attachment, this record's §3, means nothing on the network until CHG-0007 is done.

**Per-device Wi-Fi keys are feasible but not self-service.** The controller and the AP's firmware
list PPSK with a VLAN per key, which fits §3. But a PPSK write needs site-wide network permissions,
so an owner can't be given that credential directly without breaking ADR-0010 §3. This is
analysis; see Open question 3.

**Applications that need nothing from the platform owe it nothing.** A device with no network, like
the pumpkin, is not enrolled anywhere.

**Descriptive pages change only on acceptance.** The tenant segments and IoT inhabitants in
[Network Segmentation](/docs/architecture/network-segmentation/), the Raspberry Pi row in Tenant
Compute, and the tenant contract are left as they are while this record is Proposed.

---

## Current state

- **Proposed.** Nothing is implemented.
- The LP stand, the Ma Bell gateway and the MQTT broker remain exactly as `d8c31cd` and earlier
  commits left them. As of 2026-09-14, the broker doesn't answer at all.
- **Validated read-only on 2026-09-14:**

  | Area | Result |
  |---|---|
  | Controller PPSK and per-key VLAN | Documented |
  | AP firmware | Listed as supporting PPSK |
  | Client isolation | Guest Network plus EAP ACL is the only documented route |
  | Core router | Enforces nothing |
  | Broker | Unreachable |
- **Blocking acceptance:**
  - the device test (after CHG-0005)
  - a running broker for Open question 1
  - Open question 2
  - CHG-0007, before the IoT segment is relied on
