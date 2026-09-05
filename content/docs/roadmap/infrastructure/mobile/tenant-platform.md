---
title: "Tenant Platform"
weight: 4
tasks_completed: 1
tasks_in_progress: 3
tasks_planned: 2
---

# Tenant Platform

Deliver the capability to run **tenants** on the mobile substrate — from network architecture
through a repeatable, code-defined tenant lifecycle. Each tenant is an isolated workload that
supplies its own IaC/CaC to rebuild from scratch against the substrate.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Design tenant network architecture ✅

How tenant traffic is isolated, routed, and addressed.

- **Decided:** the fabric model — an EVPN overlay owned by the tenant compute domain,
  self-contained per hypervisor, single-member now and expandable to a cluster
  ([ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/)).
- **Decided:** the numbering scheme — the site `/16` split so tenant overlays live at
  `10.20.128.0/18` and fabric loopbacks at `10.20.255.0/24`, with every tenant identifier derived
  from a single allocated index ([ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/)).
- **Deferred — DNS:** how tenant records are authored and published into the substrate zone is
  still undecided, and is tracked as its own thread below rather than holding this milestone open.
  Proxmox's SDN DNS integration targets a PowerDNS API; the core router runs Unbound, so it does
  not fit as-is.

## Define tenant contracts ⏳

The interface every tenant must satisfy to be rebuildable against the substrate.

- What a tenant **supplies** as code: network attachment, DNS records, compute/resource
  declaration, naming.
- What the substrate **guarantees** in return: a network to attach to, a perimeter, and a DNS
  zone to publish into.
- The tenant↔substrate boundary written as a specification, so any conforming tenant can be built.

## Build the tenant fabric (Phase 1) 🔄

Stand up the single-member fabric on hv02.

**No longer gated** — hv02 runs PVE 9.2.11 and serves `/cluster/sdn/fabrics`, so the underlay is
defined as code rather than as hand-maintained node state.

- ✅ Substrate transport: `tenant_transit` (VLAN 50) and `tenant_underlay` (VLAN 51) in inventory;
  `tenant_1/2/3` removed. The tenant hypervisor's switch port is a trunk carrying both plus
  management.
- ✅ Hypervisor attachment: the bridge is VLAN-aware and the transit and underlay sub-interfaces
  are up, driven from inventory by the `proxmox_node_network` role.
- ✅ EVPN SDN as code: fabric, VTEP identity and controller applied on hv02 from
  `deevnet-tenant-factory`.
- ✅ Hypervisor default route moved onto transit, so the data plane stops riding the management
  segment.
- ✅ Tenant egress through the perimeter: transit forwarding and a default route inside each
  tenant VRF, both code-managed
  ([ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/)). Proxmox's
  own exit-node behaviour would have routed tenants *around* the perimeter onto the management
  segment.
- ⏳ Core router reduced to the perimeter (NAT, tenant↔management policy).

## Tenant DNS publication ⏳

The one part of the tenant contract still undecided: how a tenant authors its own records and
publishes them into the substrate zone so `service.tenant.site.deevnet.net` resolves.

Framed in [ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) — problem and
constraints stated, decision open.

- Proxmox SDN can register records itself, but only against a PowerDNS API — the core router runs
  Unbound, so it does not fit without a shim. Its registration is also tied to IPAM allocation,
  which the tenant module bypasses by addressing from cloud-init, so a backend alone would publish
  nothing.
- The substrate's own DNS is inventory-driven Ansible, which is the opposite of tenant-owned.
- The last open part of the tenant contract.

## Tenant provisioning tooling 🔄

A repeatable, code-defined tenant lifecycle.

- ✅ Reusable Terraform (`bpg/proxmox`) module implementing the network and compute halves of the
  tenant contract: VRF + VNet(s) + subnet + VMs from template, addressed by cloud-init.
- ✅ One tenant = one instantiation, **in its own repository** (`deevnet-tenant-<name>`), consuming
  the module by git tag and a fabric attachment the substrate issues at onboarding (ADR-0006).
  Create, rebuild and destroy from code, with every identifier derived from one allocated index.
- ✅ A reference implementation new tenants are copied from, which **cannot itself be applied** —
  it ships with an index the module rejects, so the guard does not depend on being read.
- ✅ DNS publication over RFC 2136 with a per-zone TSIG key (ADR-0004), and a state store tenants
  may use or decline (ADR-0007).

## First tenant — end-to-end 🔄

Prove the whole path with a real tenant.

- ✅ Provisioned from code: `tdemo` (index 1, `10.20.129.0/24`), cloud-init addressed.
- ✅ Egress via the perimeter, verified from inside the workload rather than from a NAT counter —
  and verified *not* to reach the management segment on-link.
- ✅ DNS publication end to end: `dig @10.20.99.1 tdemo-1.tdemo.mobile.deevnet.net` answers
  `10.20.129.10`, and the reverse answers the name — records written by the tenant's own Terraform
  over TSIG-signed RFC 2136, served by substrate-run PowerDNS, reached through the resolver's
  forward.
- ✅ Moved to its own repository with an empty plan as the acceptance gate: same state, same
  resource addresses, same running VM, same records, zero API mutations.
- ⏳ Inter-tenant isolation — needs a second tenant to test against. Note the *state* half is
  already server-enforced: a tenant's credential is refused for another tenant's prefix.
- ⏳ Rebuild-from-scratch drill — now re-scoped to the reference implementation: create a throwaway
  tenant repository from `examples/tenant/`, apply, verify, destroy. Run at each module MAJOR tag.

---

## Future outlook: Phase 2 — tenant cluster

Not scheduled, not counted. Reached by **adding** members to the Phase 1 fabric, not rebuilding it
— same SDN objects re-applied at cluster scope, underlay peers formed, a QDevice for quorum.
Trajectory detail is in [ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/#trajectory).
The management hypervisor (hv01) follows a separate path and does not join the tenant fabric.
