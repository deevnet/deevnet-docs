---
title: "Access"
weight: 1
---

# How an Edge Device Reaches Its Application

A device is attached to an access segment. The application it belongs to runs in a tenant overlay
that nothing outside can reach. This page is how the two meet.

---

## The shape of the problem

Two facts define the whole answer, and neither is negotiable:

- **A tenant has no inbound path.** The fabric provides egress only; nothing outside a tenant can
  open a connection into it
  ([ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/)).
- **A device has no route to tenant space.** Its segment's policy permits device-facing platform
  services, and nothing else. Adding a path from the IoT segment into the tenant overlay would give
  *every* device reach into *every* tenant, which is exactly the isolation the model exists to
  provide.

So neither side can dial the other. They meet at a **rendezvous service** on the substrate that
both sides dial *out* to.

```
edge device                                    tenant workload
     │                                                │
     │  dials out                          dials out  │
     └──────────►  rendezvous service  ◄──────────────┘
                   on IoT Backend
                   authenticates both sides
```

This is not a workaround for missing routing. It is the design: the service in the middle is the
only place where "this device belongs to this application, and may consume this" can be enforced,
because it is the only place where anything proves who it is.

---

## Why the network cannot be the boundary

Devices of different owners share one segment. On that segment, **nothing in a packet distinguishes
one owner's device from another's**.

The wireless credential identifies a tenant and a trust class, not a device — one key serves every
device a tenant flashes with it. Every device draws an address from one pool on one subnet. MAC and
IP are both trivially forged by anything already attached.

So a rule of the shape *"the LP stand may reach EdS services but not Ma Bell's"* **cannot be
written as a firewall rule**, because no firewall can tell the two devices apart. This is a
property of putting mutually-distrusting devices on a shared segment, and it would remain true on a
per-owner segment too, since an owner's own devices still share Layer 2 with each other.

**Authorization is therefore carried by a credential the device proves, at or above the transport
layer** — never by its address
([ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) §2).

{{< hint info >}}
This is about **authorization** identity, and it does not contradict
[Correctness](/docs/standards/correctness/) §3.1, which defines a host's identity chain as
MAC → IP → DNS. That describes *inventory* identity — how the substrate deterministically names and
addresses something it already controls. It is not a claim that an address proves who is *speaking*
to a service. [Secure Identity](/docs/standards/secure-identity/) §1.2 already draws the same line:
a client device proves who it is; it does not merely assert it.
{{< /hint >}}

---

## Two ways to consume a service

Both are the same shape — authenticated, owner-scoped, dialed out to from both sides. They differ
in protocol semantics, and the choice belongs to the service, not to the tenant.

| | Brokered messaging | Direct service access |
|---|---|---|
| **For** | Commands, events, telemetry, state publication | Request/response, streaming, existing application protocols |
| **Protocol** | MQTT publish/subscribe | HTTP, WebSocket, TCP, UDP |
| **Scoping** | Per-device account, topics under the owner's prefix | Per-device credential mapped to permitted services |
| **Decided in** | [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) | [ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) |
| **Built?** | **Built** — broker, device registry and per-device accounts ([CHG-0015](/docs/changes/2026/0015-vernemq-broker/), [CHG-0014](/docs/changes/2026/0014-tenant-device-registry/), [CHG-0016](/docs/changes/2026/0016-broker-accounts/)) | Contract accepted, mechanism deferred |

**Messaging is preferred wherever publish/subscribe fits.** It gives store-and-forward and fan-out
for free, and a device that is asleep or unreachable is a normal condition rather than an error.

**Direct access exists because not every interaction is publish/subscribe.** A platform where every
application interaction must be translated into MQTT would be restrictive for no architectural
reason. An application may legitimately need an HTTP API, a WebSocket, or a protocol it did not
choose. What it may *not* have is a route into its own tenant network to get there.

---

## What this deliberately does not do

**It does not put the device on the tenant's network.** The device is never a member of
`10.20.{128+n}.0/24`, never uses the tenant's anycast gateway, and is never Layer 2 adjacent to a
tenant workload. Extending the tenant overlay to the access network was examined in detail and
rejected — see [ADR-0019](/docs/architecture/decisions/0019-tenant-l2-at-the-access-edge/) for why,
including why the hardware could not do it cleanly even if the architecture allowed it.

**It does not multi-home tenant workloads onto device segments.** A workload with a leg on the
device segment and a leg in its tenant is a Layer 2 path between tenants that bypasses the fabric's
VRF isolation entirely, and it breaks the rule that no host spans two segments.

**It does not open a zone-level path from devices into tenant space.** No `IoT → tenant` rule
exists, and none may be added.

---

## What is not protected

Two devices on one access segment **can reach each other**, and nothing currently prevents it.
Their traffic is switched at Layer 2 and never reaches the core router, so no zone policy can see
it. The site's access point offers no client isolation that would also preserve the service
reachability devices need, and wired devices on the segment have no isolation mechanism at all.

This is recorded as an accepted limitation rather than solved, because the distinction that matters
is between **being unable to send a packet to another device** and **being unable to authenticate
to another owner's services**. Only the second is a security boundary, and it holds: a hostile peer
can emit packets, but it cannot present a credential it does not have.

That is why every device-facing service must authenticate its callers individually. Zone policy
grants a whole segment; only the service itself decides who is speaking.
