---
title: "ADR-0011: Edge Devices Are Application-Owned and Platform-Attached"
weight: 11
---

# ADR-0011: Edge Devices Are Application-Owned and Platform-Attached

|  |  |
|--|--|
| **Status** | Accepted |
| **Accepted** | 2026-09-15, once its four open questions were answered. Questions 1–3 were settled by the operator on 2026-09-15 ([CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) Step 9's controller work made the platform side real); question 4 was settled on 2026-09-14. |
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

**The Raspberry Pis.** `dv02rpi001p01` to `dv02rpi004p01` are substrate-inventoried hosts on the
IoT segment (`10.20.30.11`–`.14`). All four are hardwired Ethernet, and the switch declares
`dv02rpi001p01` and `dv02rpi002p01` as access ports in VLAN 30.
- **They count as substrate for now** (operator decision, 2026-09-14).
- That classification is interim. The ownership test below has **not** been applied to them.
- They matter to this record because they share VLAN 30's Layer 2 with application-owned devices
  (Open question 4).

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
  - PPSK is WPA/WPA2 only. *(On 2026-09-14 no source stated the WPA version; a device test on
    2026-09-15 settled it — PPSK is WPA2 under the hood on the site's AP, see
    [Open question 3](#open-questions).)*
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
   - **Decided 2026-09-15 (operator): [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/)
     is the answer.** Owners register devices through the Deevnet API and its Terraform provider,
     which confine them to their own topic prefix. The broker behind it is VerneMQ, which asks the
     API on every connect, subscribe and publish (ADR-0012 §8).
     - **Nothing is tested end to end yet**, because the broker is not built. The API shell is
       deployed (CHG-0008), and the broker is a later change.
2. **Does an owner's device still need a substrate host record?**
   - [Naming](/docs/standards/naming/) defines a host by a deterministic MAC-to-IP mapping, and
     `dv02bgw001e01` has a DHCP reservation, an A record and CNAMEs.
   - A device identified by its credential rather than its address could lease from the IoT pool
     and be named in its owner's own zone under ADR-0004.
   - **Found 2026-09-14:** no new evidence. Nothing tested bears on it.
   - **Decided 2026-09-15 (operator): no substrate host record.** An application-owned device
     leases from the IoT pool and is named in its owner's own zone
     ([ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/)).
     - **Why:** identity is the device's credential, not its address, which is the same reasoning
       as question 4. Device churn then never becomes a substrate commit
       ([ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/)).
     - **Substrate-owned devices are unaffected.** The hardwired Pis and `dv02bgw001e01` keep their
       reservations and records, because they are substrate hosts.
     - This also settles [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/)'s open
       question 3.
3. **Shared or per-device Wi-Fi keys?**
   - A shared key per segment means one lost device exposes the key for every device on it, and
     rotation means a USB visit to every NVS-provisioned device.
   - Per-device PPSK keys, all mapped to the segment's own VLAN, give per-device revocation without
     per-tenant VLANs. *(Proven on the AP 2026-09-15; see below.)*
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
   - **Decided 2026-09-15 (operator): per-device PPSK keys, issued through the Deevnet API.** The
     API holds the controller credential and always binds a key to the device's trust-class VLAN.
     - **Until the API can issue keys**, substrate automation issues them, because a PPSK write
       needs the same controller permission as changing the site's wireless configuration. That is
       a recurring substrate act, and it is accepted as temporary rather than designed in.
     - **Proven on the device, 2026-09-15 ([CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) phase 6).**
       On the EAP650-Outdoor at firmware 1.3.11, a PPSK-without-RADIUS profile with two keys bound
       to VLAN 30 and VLAN 31 was created through the documented Open API; a client joined with
       each key in turn and landed on the matching subnet (10.20.30.x, then 10.20.31.x). **The key
       decides the VLAN on this AP.** The shared-key fallback is no longer needed. Two API details
       the test settled: PPSK is WPA2 under the hood (a `security: 4` SSID also requires the
       `pskSetting` encryption block, not only `ppskSetting`), and a per-key VLAN needs no
       controller network object — it is raw 802.1Q tagging that OPNsense serves DHCP for.
   - **Amended 2026-09-18 (operator): one key per tenant per trust class, not one per device.**
     The issuer decision above stands — the Deevnet API holds the controller credential and binds
     every key to a trust-class VLAN — and the interim is not taken: the API issues keys from the
     start, so no tenant key is ever a substrate commit. Only the granularity changed. A device's
     MAC is trivially spoofable, so binding a key to one buys no enforcement, while forcing a
     tenant to enumerate its hardware to the substrate before it can flash anything. The thing that
     *is* enforced — the VLAN — comes from the key either way. Revocation therefore lands per
     tenant per trust class, which is the boundary the substrate can meaningfully police. See
     [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §3.
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
   - **Wired devices have no isolation mechanism at all.** The hardwired Pis (What exists) share
     VLAN 30 with wireless devices. AP isolation covers only wireless clients, and the standalone
     switch declares no port isolation.
   - **The standard doesn't require isolation inside a segment.**
     [Network Segmentation](/docs/standards/network-segmentation/) §8 isolates IoT from management
     and limits inbound access, but says nothing about devices within the segment. Option C already
     accepts that *"isolation between them depends on the services and the AP."*
   - **Decided 2026-09-14 (operator): best effort, credentials first.**
     - Owners are kept apart above Layer 3, by per-device credentials and per-owner service scopes
       (§3). That is the control.
     - Wireless clients get AP isolation where the equipment can provide it: Guest Network plus an
       EAP ACL permit, **only if the device test shows it works**.
     - **Wired devices on VLAN 30 stay unisolated, and that is accepted for now.**
     - Isolating wired devices, for example with switch port isolation once the switch is adopted,
       would be a separate decision., numbered when opened:
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
3. **Record whether PPSK and Guest Network can be enabled on the same SSID at all.** The isolation
   route in Open question 4 needs both on the IoT SSID. If the controller or AP refuses the
   combination, record it: per-device keys and AP isolation then can't coexist on one SSID, and
   Open question 4's decision needs revisiting.
4. **Record whether a wired device and a wireless test client on VLAN 30 reach each other.** Use a
   hardwired Pi such as `dv02rpi001p01` (`10.20.30.11`). They are expected to, because AP isolation
   covers wireless clients only. The test confirms that the wired gap accepted in Open question 4 is
   the gap that actually exists.
5. Record the WPA versions the controller offers for the PPSK SSID.
6. Remove the test SSID, profile and ACL.

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

**Descriptive pages changed on acceptance.** The IoT segment definition in
[Network Segmentation](/docs/architecture/network-segmentation/) was corrected on 2026-09-18. The
tenant segments, the Raspberry Pi row in Tenant Compute and the tenant contract are unchanged: the
four Pis count as substrate for now, so nothing there is wrong yet.

**The segmentation standard changed on acceptance too.**
[Network Segmentation](/docs/standards/network-segmentation/) §8 defined the IoT segment as holding
devices whose firmware is *"built, managed, and updated through the Deevnet automation pipeline."*
Under §4 of this record, firmware is built and released by its owner, from its owner's repository.
That contradicted the standard's definition. Because standards are authoritative, §8 was corrected
on 2026-09-18 to the attachment rule in §3 — controlled firmware whose owner is known — rather than
this record being written around it.

---

## Current state

- **Accepted 2026-09-15.** All four open questions are answered. The granularity of question 3 was
  amended on 2026-09-18 to one key per tenant per trust class.
- **Per-key VLANs are proven on the hardware, not merely documented.**
  [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) phase 6: on the
  EAP650-Outdoor at firmware 1.3.11, a client joined with the VLAN-30 key landed on 10.20.30.100
  and with the VLAN-31 key on 10.20.31.100. The test artifacts were torn down afterwards, so
  `DVNTM-IOT` does not exist on the controller yet and no application-owned device has Wi-Fi.
- The LP stand and the Ma Bell gateway remain exactly as `d8c31cd` and earlier commits left them.
- **The broker does not exist.** `dv02mqt001v01` was retired; VerneMQ on `dv02msg001v01` is built
  and empty.
- **Validated read-only on 2026-09-14, and where each finding now stands:**

  | Area | Result |
  |---|---|
  | Controller PPSK and per-key VLAN | Documented, and since proven on the AP |
  | AP firmware | Listed as supporting PPSK, and since proven at 1.3.11 |
  | Client isolation | Guest Network plus EAP ACL is the only documented route; still untested |
  | Core router | Enforces nothing |
  | Broker | Did not answer; since retired |
- **Still outstanding:**
  - [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/), before the IoT segment is relied
    on as a boundary. The core router still passes everything between zones.
  - A running broker, for the device-to-service half of open question 1.
  - Client isolation (open question 4). The isolation half of CHG-0005 phase 6 was not run, so
    "best effort" is currently no effort: devices on the IoT segment are not isolated from each
    other.
