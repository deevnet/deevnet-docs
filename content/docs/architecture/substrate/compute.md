---
title: "Compute"
weight: 2
---

# Substrate Compute

The compute hosts a site runs, and what each is for.

---

## Compute by purpose

A site's compute is deliberately split by **purpose**, not by capacity. Its hosts are not a cluster
and are not interchangeable:

| Host | Purpose | Carries |
|------|---------|---------|
| **Management hypervisor** | The site's own services | The [management plane](/docs/architecture/substrate/management-plane/) and [control plane](/docs/architecture/substrate/control-plane/) substrate service VMs |
| **Tenant hypervisor** | Where tenants run | The tenant fabric, and every tenant workload |
| **Pi lab** | Where tenants run, on real hardware | A small bank of single-board computers, lent to tenant projects that need a Pi rather than a VM |

Only the management hypervisor *makes up* the substrate. The tenant hypervisor and the Pi lab are
substrate hosts — inventoried, cabled and provisioned like any other — but they are **capacity the
substrate offers tenants**, not infrastructure the site depends on. Losing either stops tenant
work, never the site.

The separation is a **plane** separation as much as a workload one. The tenant hypervisor owns the
tenant fabric's control plane — its own SDN controller, its zones, its VRFs — and the management
hypervisor has no knowledge of tenant overlays at all. Each evolves independently, and neither
depends on the other to come up.

---

## Nothing is clustered

The hypervisors are **standalone**. There is no cluster, no quorum, no HA manager and no automatic
failover. A node that is down takes its guests with it until it comes back.

This was a deliberate choice rather than an omission
([ADR-0001](/docs/architecture/decisions/tenant-networking/0001-tenant-network-fabric/)): clustering two nodes
introduces quorum fragility that needs a third vote to resolve, and it would couple the management
and tenant planes into one control and failure domain — the opposite of the separation above.

The consequences reach further than availability, and they are worth knowing before relying on
anything here:

- **There is no shared storage.** VM disks live on the hypervisor's own local storage, so even if
  the nodes were clustered there would be nothing to migrate to. Losing a hypervisor is a
  rebuild-and-restore, not a failover. Shared storage is the
  [Shared Storage](/docs/roadmap/infrastructure/mobile/shared-storage/) roadmap project.
- **Nothing enforces VMID uniqueness** across the substrate, because there is no cluster
  filesystem. Inventory does it instead, through an allocator.
- **There is no network redundancy.** Each hypervisor reaches the network over a single link,
  so a failed port, cable or NIC takes the host off the network.

See [Limits](/docs/policies/risk-management/resiliency/) for the full picture of what the hardware cannot do.

---

## The tenant fabric

The tenant hypervisor runs an **EVPN/VXLAN fabric** local to itself — a single-member fabric today,
modeled so that gaining a second member is additive rather than a redesign. It carries a real VTEP
identity and an underlay even with no peers, so adding a node later is "add a neighbor" rather
than "invent an underlay after the fact."

The fabric is where tenant isolation actually lives: one VRF per tenant, with an anycast gateway
the fabric hosts. See [Tenant Networking](/docs/architecture/tenant/networking/) for the model and
[ADR-0001](/docs/architecture/decisions/tenant-networking/0001-tenant-network-fabric/) for why it was chosen over a
VLAN-aware bridge or a cluster.

---

## The Pi lab

Some tenant projects need real hardware — GPIO, a radio, an ARM board — rather than a VM. The Pi
lab is a small bank of identical single-board computers for them. It is to hardware what the tenant
hypervisor is to VMs: a shared place for tenant work, with the difference that a slot is lent for
a project rather than carved out by the API.

- **The image is the product.** A project is developed as an image on a lab host; when it is done,
  that image goes onto hardware the project owns, and the lab host is reimaged for the next one.
- **Lab hosts sit on the IoT segment**, beside the devices they are most often built to talk to,
  and away from the management plane
  ([Network Segmentation](/docs/architecture/network-segmentation/#iot-segment)).
- **Nothing depends on the lab.** No substrate service runs on it, so it can be empty, rewired or
  retired without touching the site.

---

## Architectural properties

- **Compute hosts are stateless.** They can be reprovisioned from scratch by the builder, and a
  rebuilt tenant hypervisor reconstitutes its entire fabric from code, with no peer to reconcile
  against.
- **VM placement is determined by role**, not by manual assignment: a substrate service VM goes to the
  management hypervisor, a tenant workload to the tenant hypervisor.
- **Pi lab hosts are lent, not allocated.** A tenant project borrows a slot for as long as it is
  being developed; when it works, the project moves to dedicated hardware of its own and the slot
  returns to the lab.
- **Every host's management interface sits on the management segment**, with a fixed address by
  reservation rather than configured into the host.
- **Node-local state is applied from code, never hand-carried.** Where the hypervisor platform
  cannot model a setting the design needs, automation applies it like everything else. What is
  *not* acceptable is state that contradicts configuration the platform generates and rewrites
  ([ADR-0019](/docs/architecture/decisions/tenant-networking/0019-tenant-l2-at-the-access-edge/)).
