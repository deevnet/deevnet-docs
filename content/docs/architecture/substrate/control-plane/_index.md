---
title: "Control Plane"
weight: 5
---

# Control Plane

### Purpose

The control plane is the set of services a substrate runs so it can **serve what runs on it** —
creating tenants, publishing their names, holding their secrets, brokering their devices'
connections, and collecting what they emit.

> *What does the substrate run so that tenants and devices can exist?*

It is the counterpart to the
[management plane](/docs/architecture/substrate/management-plane/), and the two are separated by
**audience**, not by technology:

| | Management plane | Control plane |
|---|---|---|
| **Answers** | How does the substrate manage itself? | How does the substrate serve what runs on it? |
| **Audience** | Operators and substrate hosts | Tenants and edge devices |
| **Segment** | Management | Platform, and IoT Backend |
| **If it is gone** | The site still routes, resolves and leases | Tenants can't be built; devices can't reach their application |
| **Holds** | Network device management, substrate observability | Provisioning, identity, tenant observability, device messaging |

Neither plane may sit on the other's segment, and no host belongs to both. Tenants must not reach
the management segment, so a service tenants use cannot live there — even though the substrate owns
it. The two also change at different rates: the substrate's own services change often, and a
restart among them must never take tenant name resolution with it.

---

## Services and where they sit

| Service | Segment | Why there |
|---|---|---|
| **Provisioning API**, and the **state store** offered to tenant infrastructure code | Platform | Tenants reach it across the tenant perimeter |
| **Tenant name service**: one delegated zone per tenant | Platform | Tenants write their own records |
| **Secret store**: the substrate's runtime credentials, the encryption of tenant secrets, the internal CA | Platform | The provisioning API and tenant-facing services read from it |
| **Tenant observability**: logs, dashboards | Platform | Tenants read their own |
| **Device messaging**: the message broker and its authentication store | IoT Backend | It serves **devices**, and devices can reach IoT Backend and nothing else inside the substrate |

**Services are placed by audience.** Each sits on exactly one segment, chosen by who uses it; a
service that would need two segments becomes two services. How these are packaged into VMs is
[Domain VMs](/docs/platforms/management-plane/domain-vms/).

### The provisioning API

The API is the control plane's center of gravity. **A tenant is created by asking the API, not by an
operator running substrate automation**
([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/)).

- **It is the only registry.** A tenant's index, from which every other identifier derives, is
  allocated by the API against its own records and the live fabric.
- **It builds what a tenant needs**: its network, its name zone and key, its state credential, its
  workloads and the names in front of them.
- **It fronts services that cannot confine a tenant themselves**, such as the wireless controller
  and the broker. The API holds their credentials and scopes every call, so no tenant holds a
  hypervisor, vault or controller credential
  ([ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/)).
- **It provisions; it is never in a data path.** An API outage stops new provisioning and nothing
  else.

The state store beside it is offered, not mandated: a tenant may keep custody of its own state
([ADR-0007](/docs/architecture/decisions/tenant-model/0007-terraform-state-custody/)).

### Device messaging

- **It is a rendezvous, not a route.** A device has no path to a tenant and a tenant has no inbound
  path, so both dial out to a service here and meet in the middle
  ([ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/)).
- **The broker authenticates from its own store**, which is never reachable from the network.
  Losing the provisioning API never disconnects a device.
- **An account's scope is derived from its tenant**, not accepted from the caller, so a malformed
  request fails closed instead of granting outside that tenant's space.
- **Device secrets and signing keys never enter the substrate's secret store.** They belong to the
  application that owns the device
  ([ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) §4).

---

## What depends on what

The control plane sits above the network and the builder, and below everything that uses it:

```
tenants, edge devices
        │  consume
control plane  ── provisioning API · tenant names · secrets · broker · tenant observability
        │  depends on
network  ── routing, firewall, resolution, addressing
        │  built by
builder  ── creates the substrate from nothing
```

**Nothing in the control plane is required to rebuild the substrate.** The builder brings up the
core network without it, and can rebuild every service in it from code. A control-plane service may
make a rebuild easier; it must never be needed for one.

The ordering has a consequence worth stating plainly: **an outage here is a provisioning outage,
not a running-workload outage.** Tenants that already exist keep running, devices that are already
connected keep working on cached credentials, and names already published keep resolving.

---

## Invariants

The control plane is correct when:

- **No host has an interface on more than one segment.** Anything crossing segments goes through the
  core router and its zone policy.
- **No host serves both planes.** A service tenants or devices reach never shares a host with a
  service the substrate runs for itself.
- **Creating a tenant requires no substrate commit.** Onboarding may; nothing that recurs may
  ([ADR-0010](/docs/architecture/decisions/tenant-model/0010-tenants-consume-platform-services/)).
- **Every service confines its callers itself.** Zone policy grants a whole segment, so a service
  that trusts a caller because it arrived from the expected VLAN has no boundary at all
  ([ADR-0020](/docs/architecture/decisions/edge-devices/0020-direct-device-access-to-tenant-services/) §5).
- **No tenant holds a credential that could reach around the API** to the services it fronts.
- **A rebuild of any one domain is a fresh install plus an apply**, not a migration.
