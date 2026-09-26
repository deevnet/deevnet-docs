---
title: "ADR-0020: Direct Device Access to Tenant Services"
weight: 20
---

# ADR-0020: Direct Device Access to Tenant Services

|  |  |
|--|--|
| **Status** | Accepted |
| **Accepted** | 2026-09-19. What is accepted is a **contract**, not a mechanism: the capability, where authorization lives, and what it must never become. The service that implements it is future work and needs no decision here. |
| **Date** | 2026-09-18 |
| **Amended** | 2026-09-18 and 2026-09-19, both before acceptance. See [What this record stopped saying](#what-this-record-stopped-saying). |
| **Scope** | How an application-owned device consumes a service belonging to its application when the broker's publish/subscribe semantics do not fit, and where the authorization boundary sits |
| **Extends** | [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) — answers its **open question 5**, *"How does a device reach a service a tenant exposes directly?"*. [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) — which built the rendezvous shape for publish/subscribe and, until amended, read as though that were the only shape. Both stay `Accepted` and unchanged in substance. |
| **Related** | [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) §2, [ADR-0019](/docs/architecture/decisions/0019-tenant-l2-at-the-access-edge/), [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/), [Network Segmentation](/docs/standards/network-segmentation/) §8–§9 |

---

## Context

[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) settled that an
application owns its devices, the platform attaches them by **trust class**, and they reach their
application through **scoped platform services**. It then opened a question it never numbered:

> **How a device reaches a service a tenant exposes directly.** This is tenant ingress, which
> ADR-0003 does not provide.

An editing error deleted the heading that would have numbered it, and it sat orphaned for six days
while [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) cited it as *"ADR-0011 open
question 5"* — a number that did not exist. This record answers it.

### The requirement, stated from the application's side

An application such as EdS owns physical devices. Those devices must be able to consume the
services their application exposes — and the shared platform capabilities they are authorized for —
over protocols the **application** chooses, with no implicit access to anything else.

The requirement is *not* "the LP stand must be in `10.20.130.0/24`". It is "the LP stand must be
able to consume the EdS services it is authorized to consume." Likewise it is not "the LP stand must
speak MQTT": an application may legitimately need HTTP, WebSocket, plain TCP or UDP, and a platform
where every interaction must be translated into publish/subscribe is restrictive for no
architectural reason.

ADR-0011 already anticipated this. Its Access axis reads *"Rendezvous services on IoT Backend,
**such as** the broker"* — a shape, not a protocol. This record makes that explicit and says what
the shape requires.

### What was verified before deciding

| Fact | Source |
|---|---|
| A PPSK key is **per tenant per trust class, not per device**. One key serves every device the tenant flashes with it | ADR-0012 §3, amended 2026-09-18 by [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) |
| A MAC binding "buys no enforcement... a MAC is trivially spoofed" | ADR-0012 §3 |
| The device registry is **unbuilt** — `GET /v1/devices` returns `501` through the `/v1/` catch-all | `deevnet-provisioning-api` `internal/server/server.go` |
| The API's finest authorization granularity today is the **tenant name**; there is no device type, and no MAC or IP is used in any authorization decision | `internal/server/principal.go`, `internal/tenant/` |
| **"A VM never spans two segments."** "A domain that needs two segments becomes two VMs. Anything that crosses segments goes through the core router and its zone policy" | [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) §2 |
| `iot -> iot_backend` is a permitted flow in the standard **and already declared** in the site's policy | [Network Segmentation](/docs/standards/network-segmentation/); `mobile/group_vars/all/firewall.yml` |
| `dv02msg001v01` (IoT Backend, VLAN 35) already holds the charter *"later other device rendezvous services"* | ADR-0013 §1 |
| The zone policy is **not enforced today** — the core router passes all traffic between every segment, demonstrated from a real client on 2026-09-18 | ADR-0011 Validation; [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/) phase 5 |
| Devices of different owners share VLAN 30's Layer 2, and nothing separates them today | ADR-0012; ADR-0011 open question 4 |

### The finding that shapes everything else

**There is no device identity at the network layer, and there is no way to create one there.**

A PPSK key identifies a tenant and a trust class. Every device of every tenant on the IoT segment
draws an address from one pool on one subnet. MAC and IP are both forgeable by anything already on
that segment. So a policy of the shape

```
LP Stand   -> EdS authorized services    ALLOW
LP Stand   -> Ma Bell services           DENY
```

**cannot be enforced by firewall or routing policy**, because no packet carries anything that
distinguishes an LP Stand from a Ma Bell device. This is not an implementation gap to be closed
later; it is a property of putting mutually-distrusting devices on one subnet, and it would remain
true on a per-tenant segment too, since a tenant's own devices still share Layer 2 with each other.

**This is about *authorization* identity, and it does not contradict the standards.**
[Correctness](/docs/standards/correctness/) §3.1 defines a host's identity chain as MAC → IP → DNS,
and [Identity vs Intent](/docs/standards/identity-vs-intent/) lists MAC and IP as identity
variables. Both are describing **inventory** identity — how the substrate names and addresses a
thing it already controls, deterministically and from code. Neither is a claim that an address
proves *who is speaking* to a service. For that,
[Secure Identity](/docs/standards/secure-identity/) §1.2 already has the rule: *"A client device is
allowed to prove who you are — it should not permanently store what you know."*

The authorization boundary must therefore be **cryptographic, at or above the transport layer**.
Network policy below it is defense in depth and nothing more.

---

## Options considered

### A — Broker only *(status quo)*

Devices reach tenants only through the MQTT broker, with per-device credentials and per-topic ACLs.

- **Pros:** identity is cryptographic and per-device; nothing new to build; fits every device that
  can speak MQTT.
- **Cons:** publish/subscribe does not fit every workload. A device needing request/response, bulk
  transfer, streaming or an existing HTTP protocol has no path at all, and the application is
  forced to tunnel its semantics through a broker that was not chosen for them.
- **Verdict:** remains correct and preferred **wherever its semantics fit**. It is not sufficient as
  the only answer.

### B — Tenant backends multi-homed onto the device segment

A tenant workload takes a second NIC on the device segment, with IP forwarding disabled.

- **Pros:** nothing to build; the backend talks to devices directly.
- **Cons:**
  - **It breaks [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) §2
    outright** — *"A VM never spans two segments."*
  - **It creates a cross-tenant Layer 2 path in the substrate.** Two tenants' backends, each
    holding a NIC on the shared segment, are Layer 2 adjacent **to each other**. A compromised EdS
    backend reaches a Ma Bell backend directly, and the VRF isolation that is the entire basis of
    [ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/)'s tenant separation is
    routed around by two second NICs.
  - **`ip_forward=0` is a default, not a boundary.** Root on a compromised backend flips it, and
    forwarding is not even needed to relay — any process can read one socket and write another.
  - It couples tenant service placement to substrate networking, so where a tenant runs a service
    becomes a substrate concern.
- **Verdict:** **Rejected.** The cross-tenant path is disqualifying on its own.

### C — A dedicated, more contained device segment

A second access segment for devices needing direct access, with no route off itself, its own SSID,
and a service edge holding the only address on it.

- **Pros:** the smallest blast radius; containment by construction rather than by policy.
- **Cons:**
  - **The containment it promises is not achievable alongside a proxy.** A service that receives
    device connections *and* reaches tenant services either needs a route off the segment — in
    which case containment is policy again — or a second interface, which is option B wearing a
    substrate badge.
  - **It splits a trust class by purpose.** Devices needing direct access and devices using the
    broker run the same owner-controlled firmware and carry identical trust. Giving them different
    segments is attachment by *purpose*, which is the same category error as attachment by *owner*
    — the thing ADR-0011 §3 exists to prevent.
  - Every bit of it is substrate that has to exist before the first consumer does.
- **Verdict:** **Rejected as unnecessary.** It was the draft's answer; see
  [What this record stopped saying](#what-this-record-stopped-saying).

### D — Per-device certificates with 802.1X

Identity established at attachment: the AP authenticates each device against RADIUS and assigns a
VLAN per device (`wirelessVlanAssignment` exists in the controller's served spec).

- **Pros:** the strongest identity, established before an address is issued.
- **Cons:** a RADIUS service, a device PKI, and per-device certificates provisioned onto
  ESP32-class hardware over USB — large new substrate for a problem the transport layer solves.
- **Verdict:** **Not now.** Recorded because it is the right answer if identity ever needs to be
  established at *attachment* rather than at *connection*.

### E — A device-facing service on IoT Backend *(chosen)*

The device stays on the access segment of its trust class. The service it consumes is a
platform-run, owner-scoped service on **IoT Backend**, reached over the `iot -> iot_backend` flow
the standard already permits and the site already declares. It authenticates the device
cryptographically and serves only what that device's registration authorizes.

- **Pros:**
  - **This is ADR-0011's existing shape**, not a new one. The broker is the instance that exists;
    this is the same rendezvous with different protocol semantics.
  - **Zero new substrate.** No segment, no SSID, no VLAN, no DHCP or DNS change, no new zone rule.
    ADR-0013 §1 already gives the device-messaging VM the charter for *"later other device
    rendezvous services."*
  - Every VM keeps one segment, so ADR-0013 §2 holds and no cross-tenant Layer 2 path exists.
  - It works for tenantless applications, exactly as ADR-0011 requires.
- **Cons:**
  - It is a component to build, and for anything beyond plain TCP it is protocol-aware.
  - It concentrates value: it holds the map from device identity to tenant services.
  - Honestly described, it is a second broker. See [Consequences](#consequences).

---

## Decision

**Option E**, and what is accepted is the contract below rather than any particular service.

### 1. Direct service access is a platform capability

Deevnet supports **authenticated, owner-scoped direct access** from an application-owned device to
a service belonging to its application, for protocols where broker semantics do not fit. It is a
first-class capability, not a concession for an awkward device.

MQTT remains **preferred wherever publish/subscribe fits**, because it is built, because it gives
store-and-forward and fan-out for free, and because a strong application-level boundary is better
than a thin one. Direct access exists for the cases it does not fit. The choice is a property of
the **protocol and the service**, not of the tenant.

### 2. Authorization is cryptographic, at or above the transport layer

A device's authorization to consume a service is carried by a **credential it proves**, never by
its address. MAC and IP are forgeable on a shared segment and are not authorization inputs.

The PPSK / network credential establishes only *attachment*: that this connection belongs to a
tenant, in a trust class, permitted onto this access network. **Attachment is not authorization.**
Joining `DVNTM-IOT` does not mean a device may consume everything reachable from VLAN 30.

The concrete credential mechanism is **not decided here** — mTLS, a token, or something the device
PKI layer brings later. ADR-0012 §3 already defers "identity and PKI" to its own record, and this
record does not pre-empt it.

### 3. Direct access does not grant tenant network membership

The device does not join the tenant's overlay, is not addressed from it, and is not Layer 2
adjacent to it. Attachment remains by **trust class**
([ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) §3);
[ADR-0019](/docs/architecture/decisions/0019-tenant-l2-at-the-access-edge/) holds.

### 4. Two shortcuts are closed

- **Tenant workloads are not multi-homed onto device segments.** Option B's reasoning applies to
  any workload, tenant or substrate: a VM that spans the device segment and a tenant segment is a
  cross-tenant Layer 2 path regardless of who owns it.
- **`IoT -> tenant_transit`, or `IoT -> tenant networks`, is not the answer.** A zone-level allow
  from the device segment into tenant space would give every device reach into every tenant, which
  destroys the owner-scoping this record exists to provide. It must not be added.

### 5. The invariant that makes the shared segment safe

**Every device-facing service on IoT Backend authenticates its callers per device.**

This follows from the two facts above it and is load-bearing: zone policy grants the **whole
zone**, so once CHG-0007 runs, any device on the IoT segment may reach any service on IoT Backend
at the network level. Network policy decides *which segments may speak*; only the service decides
*who is speaking*. A device-facing service that trusts its callers because they arrived from the
right VLAN has no boundary at all.

This is what makes the unresolved peer-isolation limitation (below) tolerable, and it is why the
limitation is an accepted cost rather than an architectural failure.

---

## What this record stopped saying

Two drafts preceded acceptance, and both are recorded rather than quietly replaced.

**2026-09-18 — a routeless segment and a proxy cannot coexist.** The first draft asserted both that
the device segment would carry no gateway and no router interface, and that a service edge on it
would proxy to tenant services. Those are incompatible: the edge must receive device connections
*and* reach tenant services, and with no route off the segment the only way to do both is a second
interface — which is option B. The "structural containment" claim was not a property the design
ever had.

**2026-09-19 — the dedicated segment was unnecessary.** The second draft kept a dedicated
`iot_contained` segment with its own VLAN, its own SSID, prescribed DHCP and DNS behavior, an
exact firewall rule and a named VM placement. All of it is removed. It was invented to buy
containment that the zone policy delivers anyway, and separation between device classes that carry
**identical trust** — splitting a trust class by purpose is the same error as splitting it by
owner. The existing `iot -> iot_backend` flow already carries this capability with no new substrate
at all.

What survived both drafts is what did not depend on the mechanism: the identity finding, the
multi-homing rejection, the closed shortcuts, and §5's invariant. That is the whole of the
contract, and it is what is accepted.

**A dedicated segment is not forbidden — it is unjustified.** It becomes justified only by a
genuine **trust** difference between device classes, at which point it is a new trust class under
ADR-0011 §3 and gets its own record.

---

## Consequences

### Positive

- ADR-0011's open question 5 is answered without amending ADR-0011's decision, and without adding a
  segment, an SSID, a VLAN or a zone rule.
- An application chooses its protocol. A platform where every interaction must become MQTT is not
  what these records describe, and a future reader cannot conclude otherwise.
- The rule for which mechanism to use is semantic and stable: publish/subscribe to the broker,
  everything else to a direct service, both owner-scoped and both authenticated per device.
- Tenant workloads stay on exactly one segment, so no cross-tenant Layer 2 path is created.

### Negative / accepted

- **This is a second broker.** It is an authenticating, authorizing rendezvous between devices and
  tenant services, differing from the MQTT broker in protocol rather than in purpose. Accepting
  this record accepts that the estate will eventually run two, and that a service must choose
  between them.
- **It concentrates value.** Whatever implements it holds the device-to-service map for every
  tenant, which makes it a higher-value target than the broker.
- **Nothing is built.** The device registry answers `501`, no broker runs, and no direct service
  exists. The contract is accepted; the mechanism waits. This is deliberate — the alternative was
  freezing an implementation before a single consumer existed.
- **Devices on a shared segment can still reach one another.** See below.

### Neutral

- Option A stays the default. This record does not push anything toward direct access that
  publish/subscribe already serves.
- Option D stays available if identity ever needs to move to attachment time.

---

## Peer devices on a shared segment: an accepted limitation

Devices of different owners share VLAN 30, and **nothing separates them today**. This is not fixed
by CHG-0007 and cannot be: traffic between two devices on one VLAN is switched at Layer 2 and never
reaches the core router.

What the access hardware can actually do, from the 2026-09-14 validation and vendor documentation:

- The controller's SSID schema has **no client-isolation field**. Omada folded SSID Isolation into
  its **Guest Network** setting, which also blocks clients from reaching *"any private IP subnet"* —
  which is where every service they need lives.
- The documented workaround is Guest Network plus an EAP ACL permit to a specific destination, and
  the vendor does not state whether client isolation survives the permit.
- TP-Link states that access control *"can't take effect to wireless clients which connected with
  the same SSID of same AP."*
- **Wired devices have no isolation mechanism at all**, and AP isolation would not cover them.
- Whether PPSK and Guest Network can be enabled on **the same SSID at all** has never been tested;
  ADR-0011 open question 4 turns on it.

**Why this does not threaten the architecture.** The distinction that matters is between *being
unable to send a packet to another device* and *being unable to authenticate to another owner's
services*. Only the second is a security boundary, and §5's invariant provides it: a hostile peer
can emit packets but cannot consume what it cannot authenticate to.

**It does not justify per-tenant segments.** Those would not fix it either — a tenant's own devices
still share Layer 2 with each other — and ADR-0019 rejects the mechanism on independent grounds.

---

## How a compromised device is contained

Assumes CHG-0007 has run; where it has not, every row below is currently open.

| Target | Outcome | Why |
|---|---|---|
| Another device on the same segment | **Not contained.** No isolation exists today, wireless or wired. | Accepted limitation, above |
| Another owner's service | **Blocked** — it cannot present that owner's credential. | Decision §2 and §5 |
| Another tenant's backend | **Blocked** — no tenant workload is on a device segment. | Decision §4 |
| Its owner's tenant network, beyond authorized services | **Blocked** — it reaches a platform service, which opens only what its registration authorizes. It is never on the tenant's network. | Decision §3 |
| Management, storage, trusted, platform | **Blocked by zone policy** — the IoT segment's only declared destination is IoT Backend. | CHG-0007 |
| Any tenant network directly | **Blocked, and must stay so.** No `IoT -> tenant_transit` rule exists and none may be added. | Decision §4 |
| The internet | **Permitted, by design** — the standard rates IoT as allowing controlled outbound access. | Segmentation §8 |
| Impersonating another device | **Blocked at the service, not on the network.** IP and MAC are forgeable; the credential is not. | The finding in Context |

Every boundary that holds is either a **zone rule** or a **credential**. Every boundary that would
depend on the network distinguishing one device from another does not hold, and none can be made
to.

---

## What would reopen this

- **A device that cannot hold a credential at all.** The contract assumes a device can prove
  something. One that cannot needs a different answer, probably option D.
- **A genuine trust difference between device classes**, which would make a second access segment a
  new trust class under ADR-0011 §3 rather than the convenience this record rejected.
- **A protocol requiring Layer 2 adjacency**, which is
  [ADR-0019](/docs/architecture/decisions/0019-tenant-l2-at-the-access-edge/)'s question, not this
  one.
- **PPSK and Guest Network proving mutually exclusive**, which would not change this contract but
  would settle ADR-0011 open question 4 against isolation and make §5's invariant the only control
  between peers.

## Implementation notes, for whoever builds it

Not decisions, and deliberately not settled here:

- **Protocol surface.** Plain TCP keyed on the presented credential is the minimum; HTTP-aware
  routing is more useful and more work. A real consumer's requirement should decide this, not this
  record.
- **Placement.** ADR-0013 §3 puts a new service on the VM of its domain, on that domain's segment —
  which is the device-messaging VM on IoT Backend. ADR-0013 also names the cost: *"Containers in one
  VM share its fate: a reboot takes all of them."* Whether direct and brokered access should fail
  together is an availability question for a real requirement.
- **Order of work.** The device registry comes first. Until `/v1/devices` exists there is nothing to
  record a device's permitted services in, and the contract's §2 and §5 have no state to draw on.
- **Connection direction is not a choice any more.** *Added 2026-09-19, once
  [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) applied the zone policy.* The site
  declares `tenant_transit -> iot_backend` and **not** its reverse. So a tenant workload may dial
  **out** to a service on IoT Backend, and a service on IoT Backend **cannot** dial into a tenant.
  The rendezvous is therefore a place both sides connect to — tenant outbound, device inbound —
  and never a proxy that reaches into the overlay on the device's behalf. That was already the
  broker's shape; it is now enforced rather than intended, and an implementation that assumes it
  can originate toward a tenant will be dropped by default deny with no rule to relax, because
  §4 forbids the rule that would relax it.
