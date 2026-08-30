---
title: "Tenant Platform"
weight: 4
tasks_completed: 0
tasks_in_progress: 1
tasks_planned: 4
---

# Tenant Platform

Deliver the capability to run **tenants** on the dvntm substrate — from network architecture
through a repeatable, code-defined tenant lifecycle. Each tenant is an isolated workload that
supplies its own IaC/CaC to rebuild from scratch against the substrate.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Design tenant network architecture 🔄

How tenant traffic is isolated, routed, and addressed.

- **Decided:** the fabric model — an EVPN overlay owned by the tenant compute domain,
  self-contained per hypervisor, single-member now and expandable to a cluster
  ([ADR-0001]({{< relref "/docs/architecture/decisions/0001-tenant-network-fabric" >}})).
- **Open — DNS:** how tenant records are authored and published into the substrate zone, and who
  resolves tenant names. *This is the open thread keeping this milestone in progress.*
- **Open — numbering:** a globally-unique scheme for VNIs, VRF IDs, and tenant subnets.

## Define tenant contracts ⏳

The interface every tenant must satisfy to be rebuildable against the substrate.

- What a tenant **supplies** as code: network attachment, DNS records, compute/resource
  declaration, naming.
- What the substrate **guarantees** in return: a network to attach to, a perimeter, and a DNS
  zone to publish into.
- The tenant↔substrate boundary written as a specification, so any conforming tenant can be built.

## Build the tenant fabric (Phase 1) ⏳

Stand up the single-member fabric on hv02.

- EVPN SDN as code: controller, zone, VRF-per-tenant, anycast gateway, fabric IPAM/DHCP.
- Underlay/VTEP identity; transit VLAN to the core router; switch port trunked for transit +
  underlay (no per-tenant VLAN).
- Core router reduced to the perimeter (NAT, tenant↔management policy).

## Tenant provisioning tooling ⏳

A repeatable, code-defined tenant lifecycle.

- Reusable Terraform (`bpg/proxmox`) module implementing the tenant contract: SDN objects + VMs
  from template + DNS publication.
- One tenant = one instantiation; create, rebuild, and destroy from code.

## First tenant — end-to-end ⏳

Prove the whole path with a real tenant.

- Provision from code; verify addressing from the fabric, egress via the perimeter, inter-tenant
  isolation, and rebuild-from-scratch.

---

## Future outlook: Phase 2 — tenant cluster

Not scheduled, not counted. Reached by **adding** members to the Phase 1 fabric, not rebuilding it
— same SDN objects re-applied at cluster scope, underlay peers formed, a QDevice for quorum.
Trajectory detail is in [ADR-0001]({{< relref "/docs/architecture/decisions/0001-tenant-network-fabric" >}}#trajectory).
The management hypervisor (hv01) follows a separate path and does not join the tenant fabric.
