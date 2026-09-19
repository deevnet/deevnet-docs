---
title: "ADR-0020: Direct Device Access to Tenant Services"
weight: 20
---

# ADR-0020: Direct Device Access to Tenant Services

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-18 |
| **Amended** | 2026-09-18, before acceptance. The first draft asserted both a routeless segment and a service edge that proxies to tenant services. Those are incompatible — see [Decision §2](#2-the-segment-is-routed-and-containment-is-policy). Containment is policy, not structure, and the edge's placement follows from that. |
| **Scope** | How a physical device reaches a tenant service directly, when the broker's publish/subscribe semantics do not fit the protocol; what segment it attaches to, and where the authorization boundary sits |
| **Depends on** | [ADR-0011: Edge Devices Are Application-Owned and Platform-Attached](/docs/architecture/decisions/0011-edge-devices-application-owned/), [ADR-0012: IoT Platform Services Through a Deevnet API](/docs/architecture/decisions/0012-iot-platform-api/) |
| **Related** | [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/), [ADR-0019: Tenant Layer 2 at the Access Edge](/docs/architecture/decisions/0019-tenant-l2-at-the-access-edge/), [ADR-0018: Operator Access to Tenant Workloads](/docs/architecture/decisions/0018-operator-access-to-tenants/), [Network Segmentation](/docs/standards/network-segmentation/) §8–§9 |
| **Blocked on** | The device registry. `GET /v1/devices` returns `501 Not Implemented` today. |

---

## Context

[ADR-0019](/docs/architecture/decisions/0019-tenant-l2-at-the-access-edge/) closed the question of
whether a tenant's overlay may reach the air. It named the test that would re-open the subject: *a
protocol that genuinely needs Layer 2 adjacency.* This record answers the weaker and much more
common case — a device that needs **direct TCP, UDP, HTTP or WebSocket connectivity to a tenant
service**, where the broker's semantics do not fit, but Layer 2 adjacency is not actually required.

The operator's proposal, evaluated here, is deliberately built to respect the invariant ADR-0019
defended:

> `VLAN = device trust/access class`, **not** `VLAN = tenant identity`.

One shared access segment represents a class of devices. Every tenant's direct-access devices share
it. Tenant #63 creates no VLAN. That framing is correct, it is preserved by the decision below, and
the proposal does **not** drift into per-tenant VLANs.

It drifts somewhere else, and this record exists mostly to name that: once a device needs
authenticated, per-service authorization for arbitrary protocols, **what you are building is a
broker that speaks TCP instead of MQTT.** That may well be worth building. It should not happen by
accident, and it should not be mistaken for a networking change.

### What was verified before deciding

| Fact | Source |
|---|---|
| A PPSK key is **per tenant per trust class, not per device**. One key serves every device the tenant flashes with it | [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §3, amended 2026-09-18 by [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) |
| A MAC binding "buys no enforcement... a MAC is trivially spoofed" | ADR-0012 §3 |
| The device registry is **unbuilt**. `GET /v1/devices` returns `501 Not Implemented` | `deevnet-provisioning-api` `internal/server` |
| **"A VM never spans two segments."** "A domain that needs two segments becomes two VMs. Anything that crosses segments goes through the core router and its zone policy" | [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) §2 |
| No SSID-level client-isolation field exists in the controller's served API spec; `guestNetEnable` is the only per-SSID separation setting | [ADR-0011 Validation](/docs/architecture/decisions/0011-edge-devices-application-owned/#wireless-client-isolation), 2026-09-14 |
| Guest Network blocks clients from reaching "any private IP subnet" as well as each other | TP-Link, via the same validation |
| "Access Control function can't take effect to wireless clients which connected with the same SSID of same AP" | TP-Link, via the same validation |
| The core router currently passes all traffic between every segment | ADR-0011 Validation, 2026-09-14 |
| A trust class is derived automatically from any `deevnet_vlans` segment declaring `wifi_security: ppsk` | `deevnet.mgmt` `roles/deevnet_api/defaults/main.yml` |
| Substrate segments follow `10.20.{vlan_id}.0/24`, and `10.20.128.0/18` is tenant overlay space | [ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/) |

That last row is a constraint on the segment's number: a VLAN ID at or above 128 would generate a
subnet inside tenant space. **A direct-access segment must take a VLAN ID of 127 or below.**

### The finding that shapes everything else

**There is no device identity at the network layer, and there is no way to create one there.**

A PPSK key identifies a tenant and a trust class. Every device of every tenant on the shared segment
draws an address from one pool on one subnet. MAC and IP are both forgeable by any device on that
segment. So a policy of the shape

```
LP Stand   -> EdS authorized service    ALLOW
LP Stand   -> Ma Bell services          DENY
```

**cannot be enforced by firewall or routing policy**, because no packet carries anything that
distinguishes an LP Stand from a Ma Bell device. This is not an implementation gap to be closed
later; it is a property of putting mutually-distrusting devices on one subnet.

The authorization boundary must therefore be **cryptographic**, at or above the transport layer.
Network policy below it is defense in depth and nothing more.

---

## Options considered

### A — Broker only *(status quo)*

Devices stay on `iot` (VLAN 30) and reach tenants through the broker, with per-device credentials
and per-topic ACLs under the tenant's prefix.

- **Pros:** built (in design), identity is cryptographic and per-device, no new segment, no new
  substrate.
- **Cons:** publish/subscribe does not fit every workload. A device needing request/response, bulk
  transfer, streaming or an existing HTTP protocol has no path.
- **Verdict:** remains correct wherever its semantics fit, and remains the default.

### B — Shared segment with multi-homed tenant backends *(as proposed)*

One shared access segment; tenant backends that need direct device traffic take a second NIC on it,
with IP forwarding disabled.

- **Pros:** no proxy to build; the backend talks to devices directly; preserves `VLAN = trust class`.
- **Cons:**
  - **It breaks ADR-0013 §2 outright.** A VM never spans two segments; a domain needing two becomes
    two VMs.
  - **It creates a cross-tenant Layer 2 path in the substrate.** Two tenants' backends, each holding
    a NIC on the shared segment, are Layer 2 adjacent to each other. A compromised EdS backend
    reaches a Ma Bell backend directly, and the fabric's VRF isolation — the entire basis of
    [ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/)'s tenant separation — is
    simply routed around by two second NICs.
  - **`ip_forward=0` is a default, not a boundary.** Root on a compromised backend flips it. And
    forwarding is not even needed to relay: any process can read one socket and write another.
  - It couples tenant workloads to a substrate segment, so a tenant's service placement becomes a
    substrate concern.
- **Verdict:** Rejected. The cross-tenant path is disqualifying on its own.

### C — Shared contained segment with a substrate service edge *(chosen)*

One shared access segment with **no gateway and no route off itself**. A single substrate-owned
service edge holds the only address on it and terminates device connections, authenticating each
device cryptographically and proxying to the tenant service its registry entry authorizes.

- **Pros:**
  - Every VM keeps one segment (ADR-0013 §2 holds). Tenant backends never touch the segment.
  - No cross-tenant Layer 2 path exists, because no tenant workload is attached.
  - The segment is non-routable **by construction**, so a firewall mistake cannot open it — which
    matters given that the core router currently passes all traffic between every segment.
  - Identity is cryptographic, which is the only thing that can carry the policy.
  - Policy is generated from the same registry that already shapes broker ACLs.
- **Cons:**
  - It is a component to build, and it is a proxy — protocol-aware for anything beyond plain TCP.
  - The edge is a single point of failure for direct device access, and a high-value target: it
    holds the map from device identity to every tenant service.
  - Honestly described, it is a second broker. See [Consequences](#consequences).

### D — Per-device certificates with 802.1X

Identity established at attachment: the AP authenticates each device against RADIUS and assigns a
VLAN per device (`wirelessVlanAssignment` exists in the controller's served spec).

- **Pros:** the strongest identity, established before an address is issued.
- **Cons:** a RADIUS service, a device PKI, and per-device certificates provisioned onto ESP32-class
  hardware over USB. Large new substrate for a problem option C solves above the transport layer.
- **Verdict:** Not now. Recorded because it is the right answer if device identity ever needs to be
  established at attachment rather than at connection.

### E — Reuse the IoT Backend segment

Place the tenant's device-facing service on `iot_backend` (VLAN 35) and let `iot` devices reach it,
which [Network Segmentation](/docs/standards/network-segmentation/) already lists as a permitted
flow.

- **Pros:** zero new substrate. The path is already modeled and already permitted.
- **Cons:** policy granularity is the zone, not the device — every IoT device may reach every IoT
  Backend service. It also puts tenant services on a substrate segment, with the same coupling
  objection as B, though without B's second NIC.
- **Verdict:** Not chosen, but it is the correct answer for any service where **zone-level
  granularity is genuinely sufficient**, and it should be preferred over building the edge for a
  single early case.

---

## Decision

**Option C**, with three corrections to the proposal as put.

### 1. Name the class by containment, not by connectivity

The proposal's `direct_iot` and `brokered_iot` are not trust classes. Both hold devices running
owner-controlled firmware — identical trust under
[Network Segmentation](/docs/standards/network-segmentation/) §8. What separates them is
*connectivity pattern*, and a class per connectivity pattern multiplies without limit.

The honest distinction is **containment**: this segment's devices have **no route off it**. That is
a trust-relevant property and it is what the segment should be named for — `iot_contained` rather
than `direct_iot`. ADR-0011 §3's rule survives intact: attachment is still by class, never by owner.

### 2. The segment is routed, and containment is policy

The first draft of this record claimed the segment would carry **no gateway and no router
interface**, and called that "containment structural rather than policy-dependent." That claim does
not survive contact with the rest of the design, and the contradiction is recorded here rather than
quietly corrected.

**A routeless segment and a service edge cannot both exist.** The edge has to receive device
connections on `iot_contained` *and* reach tenant services. If nothing routes off the segment, the
only way it can do both is a second interface — which is precisely
[option B](#b--shared-segment-with-multi-homed-tenant-backends-as-proposed) above, rejected two
sections earlier, merely moved from a tenant workload to a substrate one. The structural claim was
wrong; it was not a property the design ever had.

So the segment is routed, and the boundary is a zone rule that names one destination:

```yaml
- from_zone: iot_contained
  to_zone: iot_backend
  action: pass
  protocol: TCP
  destination_net: "<edge>/32"
  destination_port: "<edge port>"
```

This is an existing form, not a new one. The Deevnet API's two reaches outside Platform are written
exactly this way — one source host, one destination, one port — for the same reason: *"what it may
reach is worth stating exactly."*

**DHCP still hands out no default route**, and the edge still serves DNS, NTP and firmware updates
on the segment. That keeps the device's reachable world small and makes naive malware fail closed.
It is **defense in depth**, not the boundary: a compromised device can install a static route and
reach whatever the zone policy allows.

The cost of this correction is real and worth stating plainly. Containment now depends on the zone
policy being correct, at an estate where the 2026-09-14 validation found the core router passing all
traffic between every segment. [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) is the
change that makes the matrix real, and this rule belongs in it.

### 3. It has its own SSID

Client isolation on this controller is `guestNetEnable`, which is a **per-SSID** setting. The
proposal reuses the common PPSK SSID, which would apply isolation to brokered devices as well — or,
if not enabled, leave this segment without it. A separate SSID is required for the isolation to be
targetable at all.

### 4. Where the edge runs — leading answer, not yet settled

Once the segment is routed, the edge does not need an address on `iot_contained` at all: devices
reach it through the core router, under the rule above. That makes it an ordinary single-segment
service, and [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) §3 then
places it without argument — *"a new service joins the VM of its domain, on the segment that domain
sits on."*

Its domain is **device messaging**. ADR-0013 §1 already gives `dv02msg001v01` the charter *"the
VerneMQ broker and its auth database; later other device rendezvous services"*, and an edge that
lets a device reach a tenant service is a device rendezvous service.

It is **not a new domain**. ADR-0013 §4's test is audience, not segment: the two observability VMs
got separate roles because they *"serve different audiences on different segments, so they are
different classes of host, not two instances of one."* The broker serves devices; the edge serves
devices. Same audience, same domain.

**Leading answer: the edge is a container on `dv02msg001v01`.** No new VM, no new role mnemonic, no
amendment to ADR-0013.

Two alternatives stay live, and this record does not close them:

- **A dual-homed edge on a routeless segment.** Keeps the structural containment §2 gives up, at the
  cost of amending ADR-0013 §2 to permit a named policy-enforcement exception. Arguable — the core
  router already spans every segment, and an edge enforcing mTLS and per-device bindings is a
  narrower and stronger crossing point than a zone rule. But it grants a substrate service the
  exception this record denies tenant backends, and that should be a decision rather than a
  convenience.
- **`dv02msg002v01` on `iot_contained`.** A second instance of the same role, if devices should talk
  to a local address rather than traverse the router. Not needed to make the design work; it is a
  latency and blast-radius question, not a correctness one.

### What is enforced, and where

| Boundary | Mechanism | Strength |
|---|---|---|
| Device → tenant service | mTLS at the edge; client certificate maps to owner and permitted services | **Authoritative.** The only device-granular boundary. |
| Device → anything else off-segment | Zone policy naming one host and port | **Policy.** Correct only while the matrix is enforced. |
| Device → off-segment, naive case | No default route from DHCP | **Defense in depth.** A static route defeats it. |
| Device → device | AP client isolation | **Defense in depth.** Unproven, wireless-only, and see Open questions. |
| Edge → tenant service | Ordinary routed path and zone policy | Standard. |

### Build order

**The device registry comes first.** `deevnet_iot_device` and a service-binding resource are what
make the edge's policy derivable rather than hand-written. Until `/v1/devices` exists, this segment
would be a flat subnet holding mutually-distrusting devices at one trust level, with no way to tell
them apart — **strictly worse than VLAN 30**, which at least has a broker in front of it.

---

## Consequences

### Positive

- `VLAN = trust class` is preserved. Creating a tenant creates no VLAN, and the substrate's
  one-time provisioning is a segment, an SSID and an edge.
- Tenant workloads stay on exactly one segment, so ADR-0013 §2 holds and no cross-tenant Layer 2
  path is created.
- A compromised device reaches the edge and nothing else, provided the zone policy is enforced —
  and the rule it needs is one line in the matrix CHG-0007 already exists to apply.
- Authorization derives from the same registry that shapes broker ACLs, so there is one model of
  "what may this device reach", not two.

### Negative / accepted

- **This is a second broker.** It is an authenticating, authorizing proxy between devices and tenant
  services, differing from the MQTT broker in protocol rather than in purpose. Accepting this record
  means accepting that the estate will run two of them, and that a service must choose. The
  selection rule is semantic: MQTT where publish/subscribe fits, the edge where it does not.
- The edge is a single point of failure for direct device access, and holds the device-to-service
  map for every tenant. It is a higher-value target than the broker, because it brokers more.
- The Segmentation standard gains a segment type, and `iot_contained` must be written into §8's
  neighbourhood with its own rules — notably "MUST NOT have a routed interface or a default route",
  which no existing IoT segment says.
- Device-to-device isolation on the shared segment rests on an AP mechanism that is unverified, and
  on a segment that a wired port would bypass entirely.

### Neutral

- Option E remains available and cheaper for any case where zone-level granularity suffices. This
  record does not require the edge to be built for the first such case.

---

## How a compromised device is contained

Recorded because the proposal explicitly asked for the model to be attacked, and because the answers
are the justification for the three corrections above.

| Target | Outcome | Why |
|---|---|---|
| Another device on the segment | **Degraded, not blocked.** AP isolation should stop station-to-station frames, but ARP toward the edge must still pass, so ARP poisoning remains available as a denial-of-service. Interception is prevented only if isolation holds. | Isolation is AP-enforced and unproven |
| Another device, via the wire | **Not contained.** Any wired port on this VLAN, or a second AP, sits outside AP-enforced isolation. | Isolation lives on the AP; the VLAN extends past it |
| Another tenant's backend | **Blocked** under option C — no tenant workload is on the segment. **Reachable** under the rejected option B, at Layer 2, bypassing VRF isolation entirely. | The reason B is rejected |
| Its owner's tenant network, beyond authorized services | **Blocked** — the device reaches the edge, and the edge opens only the bindings its certificate carries. | mTLS plus registry bindings |
| Management or substrate | **Blocked by policy.** The segment's only permitted destination is the edge's address and port. No default route is issued, but that is defense in depth — a static route defeats it, the zone rule does not. | Decision §2 |
| The internet | **Blocked by the same rule**, and by the absence of any pass to a WAN path. | Decision §2 |
| Impersonating another device | **Blocked at the edge, not on the network.** IP and MAC are forgeable on a shared segment; the certificate is not. | The finding in Context |

The pattern is that every boundary that holds is either **cryptographic** (mTLS at the edge) or a
**zone rule naming one host and port**. Every boundary that depends on the network distinguishing
one device from another does not hold, and none of them can be made to — which is the finding in
Context, and the reason the edge exists at all.

---

## Open questions

1. **Does Omada client isolation behave as assumed?** Specifically: does `guestNetEnable` isolation
   hold for clients on one AP with PPSK; does it hold across APs; does it survive the EAP ACL permit
   that would be required to let devices reach the edge's private address at all; and does it apply
   to broadcast and multicast. The 2026-09-14 validation established that no other per-SSID
   isolation setting exists, and that TP-Link's own guidance says Access Control "can't take effect
   to wireless clients which connected with the same SSID of same AP" — which is about ACLs rather
   than Guest Network isolation, and leaves the interaction between the two undocumented. This
   should be settled by test before the segment carries two owners' devices.

2. **What protocol surface does the edge actually need?** Plain TCP forwarding keyed on the client
   certificate is the minimum. HTTP-aware routing is more useful and more work. This decides whether
   the edge is a small component or a large one, and it should be answered by a real device's
   requirement rather than in advance.

3. **Routed segment, or a dual-homed edge?** *Resolved in direction, not in fact.* Decision §2 takes
   the routed segment and Decision §4 places the edge on `dv02msg001v01`, which needs no ADR
   amended and uses a zone-policy form the matrix already carries. The alternative — a routeless
   segment with a deliberately dual-homed edge — buys back structural containment at the price of
   amending ADR-0013 §2, and is not foreclosed here. **Nothing is built on either answer yet**, and
   the choice should be made deliberately rather than inherited from this draft.

   What would settle it: whether the zone policy is trustworthy enough to be the boundary. Today it
   is not — the core router passes everything. After CHG-0007 it should be, and the routed answer
   becomes clearly correct. If CHG-0007 stalls, the structural answer gets stronger.

4. **Is the edge one service or two?** The broker and the edge would share `dv02msg001v01` and
   therefore its fate — ADR-0013 names this cost: *"Containers in one VM share its fate: a reboot
   takes all of them."* Direct device access and brokered device access failing together may be
   acceptable, or may be the argument for `dv02msg002v01` on its own. Worth deciding with a real
   availability requirement rather than in advance.
