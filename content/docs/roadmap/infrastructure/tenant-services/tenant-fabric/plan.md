---
title: "Tenant Fabric: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/tenant-platform/
  - /projects/tenant-platform/
weight: 1
tasks_completed: 8
tasks_in_progress: 0
tasks_planned: 1
---

# Tenant Fabric: Project Plan

The network tenants run on, from its architecture to DNS publication, one of three plans for the tenant platform with [Tenant Lifecycle](/docs/roadmap/infrastructure/tenant-services/tenant-lifecycle/plan/) and [Tenant Platform Services](/docs/roadmap/infrastructure/tenant-services/platform-services/plan/).

**Roadmap item:** [Tenant Fabric](/docs/roadmap/infrastructure/tenant-services/tenant-fabric/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Design tenant network architecture ✅

How tenant traffic is isolated, routed, and addressed.

- **Decided:** the fabric model — an EVPN overlay owned by the tenant compute domain,
  self-contained per hypervisor, single-member now and expandable to a cluster
  ([ADR-0001](/docs/architecture/decisions/tenant-networking/0001-tenant-network-fabric/)).
- **Decided:** the numbering scheme — the site `/16` split so tenant overlays live at
  `10.20.128.0/18` and fabric loopbacks at `10.20.255.0/24`, with every tenant identifier derived
  from a single allocated index ([ADR-0002](/docs/architecture/decisions/tenant-networking/0002-tenant-fabric-numbering/)).
- **Deferred — DNS:** how tenant records are authored and published into the substrate zone is
  still undecided, and is tracked as its own thread below rather than holding this milestone open.
  Proxmox's SDN DNS integration targets a PowerDNS API; the core router runs Unbound, so it does
  not fit as-is.

---

## Build the tenant fabric (Phase 1) 🔄

Stand up the single-member fabric on dv02hyp002p02.

**No longer gated** — dv02hyp002p02 runs PVE 9 and serves `/cluster/sdn/fabrics`, so the underlay is
defined as code rather than as hand-maintained node state.

- ✅ Substrate transport: `tenant_transit` (VLAN 50) and `tenant_underlay` (VLAN 51) in inventory;
  `tenant_1/2/3` removed. The tenant hypervisor's switch port is a trunk carrying both plus
  management.
- ✅ Hypervisor attachment: the bridge is VLAN-aware and the transit and underlay sub-interfaces
  are up, driven from inventory by the `proxmox_node_network` role.
- ✅ EVPN SDN as code: fabric, VTEP identity and controller applied on dv02hyp002p02 from
  `deevnet-tenant-fabric`.
- ✅ Hypervisor default route moved onto transit, so the data plane stops riding the management
  segment.
- ✅ Tenant egress through the perimeter: transit forwarding and a default route inside each
  tenant VRF, both code-managed
  ([ADR-0003](/docs/architecture/decisions/tenant-networking/0003-tenant-egress-single-member-fabric/)). Proxmox's
  own exit-node behavior would have routed tenants *around* the perimeter onto the management
  segment.
- ✅ Core router confined to the perimeter (NAT, tenant↔management policy). Audited 2026-11-12: its
  only tenant interface is the transit network, the underlay has no address on it, its one tenant
  route is the overlay `/18` via the exit node that `opnsense_routes` applies, and the only rules
  naming the overlay are the three declared in inventory (operator access, ADR-0018; tenant
  developer SSH, ADR-0028). No interface, route, DHCP scope or DNS entry per tenant remains.
- ⏳ Test network isolation between two tenants' workloads, in both directions, including the path
  out through a tenant's default route to the core router and back. Network isolation is the
  requirement here; tenants share a hypervisor, and need no hardware of their own.

---

## Tenant DNS publication ✅

How a tenant authors its own records and publishes them into the substrate zone so
`service.tenant.site.deevnet.net` resolves.

- **Decided:** RFC 2136 updates with a per-zone TSIG key, into substrate-run PowerDNS, reached
  through the core router's forward
  ([ADR-0004](/docs/architecture/decisions/naming-and-dns/0004-tenant-dns-publication/)).
- Proven end to end with `tdemo` ([first tenant](/docs/roadmap/infrastructure/tenant-services/tenant-lifecycle/plan/)), and since
  [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/) issued through the Deevnet API.
- Workloads resolve through the tenant-transit resolver, not the authoritative server
  ([CHG-0011](/docs/changes/2026/0011-tenant-workload-resolver/)).

---

## Future outlook: Phase 2 — tenant cluster

Not scheduled, not counted. Reached by **adding** members to the Phase 1 fabric, not rebuilding it
— same SDN objects re-applied at cluster scope, underlay peers formed, a QDevice for quorum.
Trajectory detail is in [ADR-0001](/docs/architecture/decisions/tenant-networking/0001-tenant-network-fabric/#trajectory).
The management hypervisor (dv02hyp001p01) follows a separate path and does not join the tenant fabric.
