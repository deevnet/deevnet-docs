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

## Domains

Services are grouped into **domains** by what they are for
([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/)). Each domain is one
host on exactly one segment; a domain needing two segments becomes two domains.

| Domain | Segment | Holds | Decided in |
|--------|---------|-------|------------|
| **Provisioning** | Platform | The **Deevnet API**, which creates and builds tenants; the **state store** offered to tenant infrastructure code | [ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/), [ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/) |
| **Identity** | Platform | **Tenant authoritative DNS**, one delegated zone per tenant; the **secret store** holding the substrate's runtime credentials and internal CA | [ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/), [ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/) |
| **Tenant observability** | Platform | Logs and metrics tenants share | [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) |
| **Device messaging** | IoT Backend | The **message broker** devices connect to and its authentication store; later, other device rendezvous services | [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/), [ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) |

### Provisioning — the Deevnet API

The API is the control plane's centre of gravity, and the thing that most distinguishes today's
architecture from what preceded it. **A tenant is created by asking the API, not by an operator
running substrate automation**
([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/)).

- **It is the only registry.** A tenant's index — the single number every other identifier derives
  from — is allocated by the API against its own database and against the live fabric. Nothing is
  recorded in a hand-maintained list.
- **It builds what a tenant needs**: the tenant's network in the fabric, its DNS zone and key, its
  state credential, its workloads, and the names in front of them.
- **A tenant holds no substrate credential.** It is admitted with a single-use enrollment token and
  trades it for a token of its own on first apply. It never holds a Proxmox credential, a vault
  password or a controller login.
- **It fronts services that cannot scope a tenant themselves.** The wireless controller and the
  broker have no per-tenant confinement of their own, so the API holds their credentials and scopes
  every call ([ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/)).
- **It provisions; it is never in a device's or a workload's data path.** Devices talk to the
  broker and the wireless network. Workloads talk to whatever they were built to talk to. An API
  outage stops new provisioning and stops nothing else.

The **state store** beside it is offered, not mandated: a tenant may keep custody of its own
Terraform state. A dependency a tenant chooses is acceptable in a way an inherited one is not.

### Identity

- **Each tenant gets a delegated zone** under the site zone and writes its own records into it over
  RFC 2136, with a key scoped to that zone. The core network's resolver forwards the zone here, so
  tenant records never enter the resolver's own configuration.
- **The secret store holds the substrate's runtime credentials**, the encryption of tenant secrets
  at rest, the internal certificate authority, and the single-use enrollment tokens the API issues
  ([ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/)).
- **Device secrets and signing keys never enter it.** Those belong to the application that owns the
  device ([ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) §4).

### Tenant observability

- Tenants reach it across the tenant perimeter, as they do the rest of the Platform segment.
- It is deliberately separate from substrate observability, which sits on management where tenants
  cannot reach it. Same function, different audience, therefore a different host.

### Device messaging

This domain serves **devices**, not tenants — which is why it sits on IoT Backend rather than
Platform, and why it is described here rather than with tenants.

- **It sits where devices can reach it.** The IoT segment may reach IoT Backend; it may reach
  nothing else inside the substrate.
- **The broker authenticates from its own store**, which lives beside it, so losing the
  provisioning domain never disconnects a device.
- **It is a rendezvous, not a route.** A device has no path to a tenant and a tenant has no inbound
  path, so both sides dial out to a service here and meet in the middle. The broker is the instance
  that exists; the shape is general
  ([ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/)).
- **Only devices in the IoT trust class get an account.** The IoT Vendor segment is isolated from
  every internal segment, so an account for one of its devices could never be used.

---

## What depends on what

The control plane sits above the network and the builder, and below everything that uses it:

```
tenants, edge devices
        │  consume
control plane  ── Deevnet API · tenant DNS · secrets · broker · tenant observability
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
  ([ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/)).
- **Every service confines its callers itself.** Zone policy grants a whole segment, so a service
  that trusts a caller because it arrived from the expected VLAN has no boundary at all
  ([ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/) §5).
- **No tenant holds a credential that could reach around the API** to the services it fronts.
- **A rebuild of any one domain is a fresh install plus an apply**, not a migration.

---

## Current state

Partly built. The provisioning domain is real — the Deevnet API creates tenants today, and `eds`
and `tdemo` were both built through it. Tenant DNS and the state store are running. The broker is
decided but **not built**, so no device reaches an application through the substrate yet, and the
device registry behind it still answers `501`. Tenant observability is unbuilt.

The zone policy that makes these segment boundaries real has also never been applied — see
[CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) and
[Limits](/docs/architecture/limits/).
