---
title: "Substrate Services"
weight: 1
---

# Substrate Services

### Purpose

Substrate services are what the substrate consumes **about itself**. They manage the substrate's
network devices and observe the substrate. Operators and substrate hosts use them; tenants never
reach them.

They sit on the **management segment**, alongside the infrastructure they manage.

---

## 1. Domains

| Domain | Holds | Notes |
|--------|-------|-------|
| **Network management** | The controller for the switch and wireless access points; later, network monitoring and config backup | Applies device configuration that inventory owns ([ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/)) |
| **Substrate observability** | Logs and metrics about the substrate | Collection tooling is not yet chosen |

Automation runners and access tooling (jump hosts) belong to this side of the plane as well. When
they are built, each joins the domain it fits, or becomes a new one.

### 1.1 Network management

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

### 1.2 Substrate observability

- **It collects by pull from the platform and IoT backend segments.** The zone policy lets neither
  of those segments reach management, so their hosts can't push to it.
- **Hosts on the management segment can push to it.**
- It is separate from tenant observability, which sits on the platform segment where tenants can
  reach it. The two serve different audiences on different segments, so they are different domains.

---

## 2. Design Principles

Substrate services follow a strict set of principles:

- **Stability over velocity**
- **Explicit configuration over convenience**
- **Recoverability over optimization**
- **Isolation from tenant experimentation**

These services are intentionally boring. That is a feature.

---

## 3. Service Characteristics

| Attribute | Requirement |
|--------|------------|
| **Availability** | High (relative to lab scale) |
| **Identity** | Stable and deterministic |
| **Network addressing** | Static via DHCP reservations |
| **Backup** | Mandatory for anything that is not derived state |
| **Rebuild support** | Must assist rebuilds, not depend on them |

---

## 4. Failure Philosophy

If something breaks:

- Tenant workloads may be destroyed and rebuilt
- The core network keeps routing, resolving and leasing without this plane
- The builder can rebuild any substrate service from code

A substrate service can make recovery easier. It must never be required for it.
