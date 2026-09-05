---
title: "Tenant Fabric (SDN)"
weight: 2
---

# Tenant Fabric — Proxmox SDN Implementation

The implementation of the tenant network model on the tenant hypervisor. The *why* and the
options considered are recorded in
[ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/); this
page is the *how* and the concrete technology choices.

---

## Overview

The tenant network is a **routed overlay** built with **Proxmox SDN** in an **EVPN zone**. Each
tenant is a VRF-isolated virtual network with an anycast gateway hosted by the fabric. The fabric
is **self-contained per hypervisor**: hv02 runs its own SDN control plane, entirely local to the
node, and is not clustered with the management hypervisor.

| Element | Choice |
|---------|--------|
| Overlay | VXLAN, EVPN control plane (FRR/BGP) via a Proxmox SDN **controller** |
| Zone type | Proxmox SDN **EVPN zone** |
| Tenant isolation | One **VRF** per tenant |
| Tenant gateway | **Anycast gateway** hosted by the fabric (the tenant subnet's `.1`) |
| IPAM / addressing | Proxmox SDN IPAM; workloads addressed by **cloud-init** (EVPN zones have no DHCP) |
| North-south exit | Single **transit VLAN** to the core router (perimeter) |
| Provisioning | Terraform, `bpg/proxmox` provider |

> **Not chosen:** VLAN-aware bridge and plain (non-EVPN) VXLAN. Both are a different paradigm
> with no distributed control plane, and adopting either would have to be torn out to reach a
> cluster. See ADR-0001, "The starter trap."

---

## Self-contained per hypervisor

Proxmox SDN configuration normally lives in the cluster filesystem and is replicated cluster-wide.
On a standalone node it is local to that node. hv02 is **standalone**, so its SDN fabric is its
own island:

- hv02 runs its own SDN controller (FRR) and its own zones, VNets, and VRFs.
- A tenant lives on hv02 and its overlay is hv02's — nothing spans to the management hypervisor.
- Rebuilding hv02 reconstitutes its entire fabric from code, with no peer to reconcile against.

This preserves the non-clustered, stateless, plane-separated design already established for the
hypervisors, and matches the goal that each tenant's IaC/CaC rebuilds it whole against the
substrate.

---

## Build requirements (do not violate — these keep the cluster door open)

From ADR-0001. Each is a hard requirement because violating it reintroduces lock-in:

| # | Requirement | Why |
|---|-------------|-----|
| 1 | **Globally-unique numbering** — VNIs, VRF IDs, tenant subnets allocated as if the fabric already spans nodes | Two members merge with no collision |
| 2 | **SDN-as-code** — all SDN objects defined in Terraform, never hand-clicked | "Cluster later" becomes a re-apply, not a migration |
| 3 | **EVPN from the start** — not a VLAN-aware bridge or plain VXLAN | Scaling is additive; the control-plane paradigm never changes |
| 4 | **Real underlay/VTEP identity now** — a proper loopback/VTEP address and an underlay concept even with no peers | Adding a member is "add a neighbor," not "invent an underlay" |

---

## Perimeter transit to the core router

The fabric hands off to the core router over a single **transit VLAN** per hypervisor
(Phase 1 choice in ADR-0001):

- Aggregate tenant egress leaves the fabric on the transit network.
- The core router sees only the transit network — never individual tenant subnets — and provides
  NAT, internet egress, and tenant↔management policy there.
- Per-tenant north-south isolation is enforced inside the fabric (VRFs), not by the core router
  seeing each tenant.

The switch port for the tenant hypervisor therefore needs the **transit VLAN** and the
**underlay** — it does **not** need a VLAN per tenant. New tenants require no switch change.

> A future option (ADR-0001, Seam 1) is a per-VRF exit with separate transit segments per tenant,
> if the core router ever needs to enforce per-tenant egress policy. Not needed for Phase 1.

---

## Provisioning with Terraform

Tenant lifecycle is managed with the **`bpg/proxmox`** Terraform provider (the API token
`terraform-prov@pve` exists for this). Terraform owns **both** the SDN objects and the VMs, so
the entire tenant — network and workloads — is declarative code.

Per-tenant flow:

1. Define the tenant's SDN objects (VRF, VNet(s), subnet, IPAM) — globally-unique numbering.
2. Clone the Packer-built Fedora template into the tenant's VNet.
3. cloud-init applies host config **and the address itself** — derived from the tenant index,
   not leased (Proxmox has no DHCP on EVPN zones).
4. Publish the tenant's DNS records into the substrate zone (tenant-owned).

A "tenant" becomes a small reusable Terraform module: **VRF + VNet(s) + N VMs from template +
DNS records**, landing on the fabric the hypervisor already provides.

---

## Trajectory: single-member fabric → cluster

The fabric is built with exactly one member today and expands without redefinition. What changes
and what stays identical is tabulated in
[ADR-0001 → Trajectory](/docs/architecture/decisions/0001-tenant-network-fabric/#trajectory).
The short version: the SDN objects, the VRF-per-tenant model, the anycast gateway semantics, and
the tenant IaC are **unchanged** when members are added; only the underlay gains peers and the
cluster gains a QDevice for quorum. Nothing structural is torn out to scale.

The management hypervisor (hv01) is on a **separate** path — it may form its own cluster for the
management plane, independently, and does not join the tenant fabric.

---

## Concrete allocation

Numbering follows [ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/). On hv02:

| Element | Value |
|---------|-------|
| Fabric | `tfab`, OpenFabric, loopback prefix `10.20.255.0/24` |
| VTEP identity | `dv02hyp002p02` = `10.20.255.2`, underlay over `vmbr0.51` |
| EVPN controller | `evpn1`, ASN `65020` |
| Transit | VLAN 50, `10.20.50.0/24`; hv02 `.22`, perimeter `.1` |
| Underlay | VLAN 51, `10.20.51.0/24`; hv02 `.22`, no router presence |
| Tenant overlays | `10.20.{128+n}.0/24`, anycast gateway `.1`, workload addresses from `.10` |

### How egress actually works

Tenant subnets carry **SNAT at the exit node**. Traffic leaving a tenant is translated to the
exit node's transit address before it reaches the core router, which is what makes ADR-0001's
promise literal: the perimeter never learns tenant address space, it only ever sees
`10.20.50.0/24`.

For that to hold, the hypervisor's default route must be on the transit interface rather than
management — otherwise tenant egress would ride the management segment. Management stays
reachable from any VLAN through source-based routing on the node: replies *sourced from* the
management address go back out the management interface, while forwarded tenant traffic still
takes the default route out transit.

## Status

**Phase 1 is built and a first tenant has working egress.**

- ✅ Transit and underlay VLANs exist on the switch and the perimeter; the tenant hypervisor's
  port is a trunk carrying both plus management.
- ✅ hv02's bridge is VLAN-aware with `vmbr0.50` and `vmbr0.51` up, driven from inventory by the
  `proxmox_node_network` Ansible role.
- ✅ The fabric, VTEP identity and EVPN controller are applied on hv02 from
  `deevnet-tenant-factory`. That repository holds the substrate side only — the fabric, the
  reusable tenant module and the index registry. **Tenants themselves are applied from their own
  repositories** (`deevnet-tenant-<name>`), consuming the module by git tag
  ([ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/)).
- ✅ Default route moved onto transit.
- ✅ First tenant end to end — `tdemo` (index 1, `10.20.129.0/24`), addressed by cloud-init, with
  internet egress through the perimeter, its names resolving through the substrate resolver, and
  its own repository.

### How egress is enforced

Two node-local settings the Ansible role owns, because Proxmox models neither
([ADR-0003](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/)):

- **Forwarding on the transit interface.** Proxmox sets `ip-forward on` only for the interfaces
  its SDN config owns, and the transit interface is node substrate. Without it, tenant traffic
  leaves and is answered but the replies are never forwarded back in — 100% loss in the VM while
  the SNAT counter climbs.
- **A default route inside each tenant VRF**, merged through `/etc/frr/frr.conf.local`. Proxmox's
  own exit-node behaviour lets a VRF lookup fall through to the node's main table, which reaches
  the management segment on-link and unSNATed. The explicit default is what makes *every*
  non-connected destination leave via the perimeter.
