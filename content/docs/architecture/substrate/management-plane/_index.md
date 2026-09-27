---
title: "Management Plane"
weight: 4
aliases:
  - /docs/architecture/substrate/management-plane/core-services/
  - /docs/architecture/substrate/management-plane/extended-services/
  - /docs/architecture/substrate/management-plane/substrate-services/
---

# Management Plane

### Purpose

The management plane is the set of services a substrate runs on its own virtual compute to
**manage and observe itself**: configuring its network devices, and collecting its logs and
metrics. Substrate automation builds these services, and they are rebuilt from code like
everything else in the substrate.

> *What does the substrate run so it can manage itself?*

Its audience is **operators and substrate hosts**. The services the substrate runs for *tenants and
devices* — the provisioning API, tenant names, the secret store, the broker — are a different plane
with a different audience, on different segments: see
[Control Plane](/docs/architecture/substrate/control-plane/). No host belongs to both.


---

## Where It Sits

The plane sits on top of the builder and the core network. It depends on both, and neither
depends on it:

| Layer | Provides | Defined in |
|-------|----------|------------|
| **Builder** | Creates the substrate from nothing, including this plane | [Builder](/docs/architecture/builder/) |
| **Network** | Routing, firewall, name resolution, address reservations, NAT, switching, wireless | [Networking](/docs/architecture/substrate/networking/) |
| **Management Plane** | Services that need compute: network device management and substrate observability | This page |

This ordering is what keeps a rebuild possible. The core network comes up without the plane, and
the builder can rebuild the plane when every service in it is gone. **The plane helps a rebuild
but is never needed for one.**

The plane's services sit on the **management segment**, alongside the infrastructure they manage.
Operators and substrate hosts use them.

---

## Services and where they sit

| Service | Segment | Why there |
|---|---|---|
| **Network device management**: the controller for the switch and access points | Management | Adopting a device needs the device and the controller on the same segment, and devices are managed on Management |
| **Substrate observability**: logs and metrics about the substrate | Management | Tenants and devices must never reach it |

Automation runners and access tooling belong to this plane too, when they are built. Services are
placed by audience, one segment each, as in the
[control plane](/docs/architecture/substrate/control-plane/#services-and-where-they-sit). How they
are packaged into VMs is [Domain VMs](/docs/platforms/management-plane/domain-vms/).

### Network management

- **Inventory owns network device configuration, and the controller applies it.** The controller
  is the actuator, not the source of truth
  ([ADR-0009](/docs/architecture/decisions/substrate/0009-network-device-config-ownership/)).
- **The controller's database is derived state.** A new controller is a fresh install that inventory
  provisions, not a migration.
- **The pre-VLAN substrate is built without it.** The core router and a standalone access switch
  come first; the controller is needed only once devices are adopted.

### Substrate observability

- **It collects by pull from the Platform and IoT Backend segments**, which the zone policy does not
  let reach Management. Hosts on Management push to it.

---

## Network Identity

Every host in the plane:

- has a **stable, predictable network identity**
- carries a **deterministic layer-2 identity**, defined in version control rather than assigned by
  whatever creates the interface
- receives a **fixed address via reservation**, keyed to that layer-2 identity, rather than an
  address configured into the host itself
- has deterministic DNS records, with services reached by name rather than by host

Addressing by reservation rather than by host configuration is what makes a rebuild
identity-preserving. The host asks for an address and is always given the same one, so nothing
inside the host has to be restored for it to return to the network as itself.

---

## Failure Philosophy

If something breaks:

- Workloads may be destroyed and rebuilt
- The core network keeps routing, resolving and leasing without this plane
- The builder can rebuild any service in the plane from code

A service in the plane can make recovery easier. It must never be required for it.

---

## Architectural Invariants

The management plane is considered **correct** when:

- the core network comes up, and a site can be rebuilt, with every service in the plane gone
- no host has an interface on more than one segment
- services with different audiences never share a host
- services are reached by stable names, so the host behind a name can be replaced without changing
  what consumers reference
- no workload code runs in the plane
- anything in it that is not derived state is backed up

If the substrate must be "mostly working" in order to rebuild the plane, the architecture is
incorrect.
