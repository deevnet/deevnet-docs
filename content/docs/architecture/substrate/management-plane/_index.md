---
title: "Management / Control Plane"
weight: 4
aliases:
  - /docs/architecture/substrate/management-plane/core-services/
  - /docs/architecture/substrate/management-plane/extended-services/
  - /docs/architecture/substrate/management-plane/substrate-services/
---

# Management / Control Plane

### Purpose

The management / control plane is the set of services a substrate runs on its own virtual compute
to **manage and observe itself**: configuring its network devices, and collecting its logs and
metrics. Substrate automation builds these services, and they are rebuilt from code like
everything else in the substrate.

> *What does the substrate run so it can manage itself?*

The same plane also hosts services the substrate offers to what runs on it. Those are described
with tenants, in [Shared Tenant Services](/docs/architecture/tenant/shared-services/).

---

## Where It Sits

The plane sits on top of the builder and the core network. It depends on both, and neither
depends on it:

| Layer | Provides | Defined in |
|-------|----------|------------|
| **Builder** | Creates the substrate from nothing, including this plane | [Builder](/docs/architecture/builder/) |
| **Network** | Routing, firewall, name resolution, address reservations, NAT, switching, wireless | [Networking](/docs/architecture/substrate/networking/) |
| **Management / Control Plane** | Services that need compute: network device management and observability | This page |

This ordering is what keeps a rebuild possible. The core network comes up without the plane, and
the builder can rebuild the plane when every service in it is gone. **The plane helps a rebuild
but is never needed for one.**

The plane's services sit on the **management segment**, alongside the infrastructure they manage.
Operators and substrate hosts use them.

---

## Domains

Services are grouped into **domains** by what they are for, not by which segment they sit on or
what kind of software they are
([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/)):

| Domain | Holds | Notes |
|--------|-------|-------|
| **Network management** | The controller for the switch and wireless access points; later, network monitoring and config backup | Applies device configuration that inventory owns ([ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/)) |
| **Substrate observability** | Logs and metrics about the substrate | Collection tooling is not yet chosen |

Automation runners and access tooling (jump hosts) belong to the plane as well. When they are
built, each joins the domain it fits, or becomes a new one.

How domains map onto hosts:

- **Each domain is one host, on exactly one segment.** Anything that crosses segments goes through
  the core router and its zone policy, so no host quietly bridges two zones.
- **A domain that needs two segments becomes two domains.**
- **Each service inside a domain stays separable.** It runs in its own container, with its own data
  and its own inventory group. Moving a service to another host is a change to inventory, not a
  redesign.
- **A new service joins the domain it belongs to.** If no domain fits, it becomes a new domain.
- **Services in one domain share the host's fate.** Rebooting a host takes all of its services
  with it, which is accepted at lab scale.
- **Services with different audiences never share a host.** The substrate's own services change
  often, and a restart among them must not take down a service something else depends on.

### Network management

- **Inventory owns network device configuration, and the controller applies it.** The controller
  is the actuator, not the source of truth.
- **The controller's database is derived state.** Whatever it holds can be rebuilt from inventory
  by re-running the automation. A new controller is a fresh install that inventory provisions, not
  a migration.
- **It sits on the management segment** because adopting a device needs the device and the
  controller on the same subnet and VLAN, and devices are managed on the management segment.
- **The pre-VLAN substrate is built without it.** The core router and a standalone access switch
  come first, and the controller is needed only once devices are adopted
  ([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) §8).

### Substrate observability

- **It collects by pull from the platform and IoT backend segments.** The zone policy lets neither
  of those segments reach management, so their hosts can't push to it.
- **Hosts on the management segment can push to it.**

---

## Provisioning

The plane is provisioned by **substrate automation**, run from the builder:

- Post-install configuration via build automation
- Management / control plane VMs are created by build automation
- Simplicity and traceability are prioritized

---

## Design Principles

- **Stability over velocity**
- **Explicit configuration over convenience**
- **Recoverability over optimization**
- **Isolation from workload experimentation**

These services are intentionally boring. That is a feature.

---

## Service Characteristics

| Attribute | Requirement |
|--------|------------|
| **Availability** | High (relative to lab scale) |
| **Identity** | Stable and deterministic |
| **Network addressing** | Static via DHCP reservations |
| **Backup** | Mandatory for anything that is not derived state |
| **Rebuild support** | Must assist rebuilds, not depend on them |

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

The management / control plane is considered **correct** when:

- the core network comes up, and a site can be rebuilt, with every service in the plane gone
- no host has an interface on more than one segment
- services with different audiences never share a host
- services are reached by stable names, so the host behind a name can be replaced without changing
  what consumers reference
- no workload code runs in the plane

If the substrate must be "mostly working" in order to rebuild the plane, the architecture is
incorrect.
