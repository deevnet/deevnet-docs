---
title: "Compute"
weight: 2
---

# Substrate Compute

The virtualization hosts a site runs, and what each is for.

---

## Two hypervisors, two purposes

A site's compute is deliberately split by **purpose**, not by capacity. The two hypervisors are not
a cluster and are not interchangeable:

| Host | Purpose | Carries |
|------|---------|---------|
| **Management hypervisor** | The site's own services | The [management plane](/docs/architecture/substrate/management-plane/) and [control plane](/docs/architecture/substrate/control-plane/) domain VMs |
| **Tenant hypervisor** | What runs on the site | The tenant fabric, and every tenant workload |

The separation is a **plane** separation as much as a workload one. The tenant hypervisor owns the
tenant fabric's control plane — its own SDN controller, its zones, its VRFs — and the management
hypervisor has no knowledge of tenant overlays at all. Each evolves independently, and neither
depends on the other to come up.

---

## Nothing is clustered

The hypervisors are **standalone**. There is no cluster, no quorum, no HA manager and no automatic
failover. A node that is down takes its guests with it until it comes back.

This was a deliberate choice rather than an omission
([ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/)): clustering two nodes
introduces quorum fragility that needs a third vote to resolve, and it would couple the management
and tenant planes into one control and failure domain — the opposite of the separation above.

The consequences reach further than availability, and they are worth knowing before relying on
anything here:

- **There is no shared storage.** VM disks live on the hypervisor's own local storage, so even if
  the nodes were clustered there would be nothing to migrate to. Losing a hypervisor is a
  rebuild-and-restore, not a failover.
- **Nothing enforces VMID uniqueness** across the substrate, because there is no cluster
  filesystem. Inventory does it instead, through an allocator.
- **Both hosts are single-NIC.** Management, tenant transit and the fabric underlay all ride one
  interface as VLAN sub-interfaces of a VLAN-aware bridge. There is no bonding and no NIC
  redundancy: a failed port, cable or NIC takes the host off the network.

See [Limits](/docs/architecture/limits/) for the full picture of what the hardware cannot do.

---

## The tenant fabric

The tenant hypervisor runs an **EVPN/VXLAN fabric** local to itself — a single-member fabric today,
modelled so that gaining a second member is additive rather than a redesign. It carries a real VTEP
identity and an underlay even with no peers, so adding a node later is "add a neighbour" rather
than "invent an underlay after the fact."

The fabric is where tenant isolation actually lives: one VRF per tenant, with an anycast gateway
the fabric hosts. See [Tenant Networking](/docs/architecture/tenant/networking/) for the model and
[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) for why it was chosen over a
VLAN-aware bridge or a cluster.

---

## Architectural properties

- **Compute hosts are stateless.** They can be reprovisioned from scratch by the builder, and a
  rebuilt tenant hypervisor reconstitutes its entire fabric from code, with no peer to reconcile
  against.
- **VM placement is determined by role**, not by manual assignment: a domain VM goes to the
  management hypervisor, a tenant workload to the tenant hypervisor.
- **Every host's management interface sits on the management segment**, with a fixed address by
  reservation rather than configured into the host.
- **Node-local state is Ansible-managed, never hand-carried.** Some things Proxmox will not model —
  a forwarding sysctl, a policy-routing unit — and those are applied from code like everything
  else. What is *not* acceptable is state that contradicts configuration Proxmox generates and
  rewrites ([ADR-0019](/docs/architecture/decisions/0019-tenant-l2-at-the-access-edge/)).
