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
is **self-contained per hypervisor**: dv02hyp002p02 runs its own SDN control plane, entirely local to the
node, and is not clustered with the management hypervisor.

| Element | Choice |
|---------|--------|
| Overlay | VXLAN, EVPN control plane (FRR/BGP) via a Proxmox SDN **controller** |
| Zone type | Proxmox SDN **EVPN zone** |
| Tenant isolation | One **VRF** per tenant |
| Tenant gateway | **Anycast gateway** hosted by the fabric (the tenant subnet's `.1`) |
| IPAM / addressing | Proxmox SDN IPAM; workloads addressed by **cloud-init** (EVPN zones have no DHCP) |
| North-south exit | Single **transit VLAN** to the core router (perimeter) |
| Provisioning | The Deevnet API, through the Proxmox API |

> **Not chosen:** VLAN-aware bridge and plain (non-EVPN) VXLAN. Both are a different paradigm
> with no distributed control plane, and adopting either would have to be torn out to reach a
> cluster. See ADR-0001, "The starter trap."

---

## Self-contained per hypervisor

Proxmox SDN configuration normally lives in the cluster filesystem and is replicated cluster-wide.
On a standalone node it is local to that node. dv02hyp002p02 is **standalone**, so its SDN fabric is its
own island:

- dv02hyp002p02 runs its own SDN controller (FRR) and its own zones, VNets, and VRFs.
- A tenant lives on dv02hyp002p02 and its overlay is dv02hyp002p02's — nothing spans to the management hypervisor.
- Rebuilding dv02hyp002p02 reconstitutes its entire fabric from code, with no peer to reconcile against.

This preserves the non-clustered, stateless, plane-separated design already established for the
hypervisors, and matches the goal that each tenant's IaC/CaC rebuilds it whole against the
substrate.

---

## Build requirements

The fabric's hard requirements — globally-unique numbering, EVPN from the start, a real VTEP
identity with no peers, every object from code — are the design's, recorded in
[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) and summarized in
[Substrate Compute → The tenant fabric](/docs/architecture/substrate/compute/#the-tenant-fabric).
Here they mean: every SDN object is created by the Deevnet API or by `deevnet-tenant-fabric`, never
hand-clicked in the Proxmox UI, so that adding a member is a re-apply rather than a migration.

---

## Perimeter transit to the core router

The handoff model is in [Tenant Networking → Perimeter handoff](/docs/architecture/tenant/networking/#perimeter-handoff).
On this node, the switch port for `dv02hyp002p02` carries the **transit VLAN** and the
**underlay VLAN** (see [Concrete allocation](#concrete-allocation)) and no VLAN per tenant, so a new
tenant needs no switch change.

---

## Provisioning

Tenant SDN objects and workloads are created by the **Deevnet API**
([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/)), which holds the
Proxmox credential; tenants never do. A tenant declares itself through the `deevnet/deevnet`
Terraform provider and the API builds, per tenant:

1. the SDN objects — EVPN zone (VRF), VNet, subnet — numbered from the tenant index it allocates;
2. workloads cloned from the Packer-built Fedora template into the tenant's VNet;
3. each workload's address, applied by cloud-init — derived from the index, not leased (Proxmox has
   no DHCP on EVPN zones).

How a tenant uses this is [Tenant Operations](/docs/runbook/tenant/).

---

## Trajectory: single-member fabric → cluster

What changes when the fabric gains a member, and what stays identical, is in
[ADR-0001 → Trajectory](/docs/architecture/decisions/0001-tenant-network-fabric/#trajectory). In
Proxmox terms: the underlay gains peers and the cluster gains a QDevice for quorum; the SDN objects
are unchanged.

---

## Concrete allocation

Numbering follows [ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/). On dv02hyp002p02:

| Element | Value |
|---------|-------|
| Fabric | `tfab`, OpenFabric, loopback prefix `10.20.255.0/24` |
| VTEP identity | `dv02hyp002p02` = `10.20.255.2`, underlay over `vmbr0.51` |
| EVPN controller | `evpn1`, ASN `65020` |
| Transit | VLAN 50, `10.20.50.0/24`; dv02hyp002p02 `.22`, perimeter `.1` |
| Underlay | VLAN 51, `10.20.51.0/24`; dv02hyp002p02 `.22`, no router presence |
| Tenant overlays | `10.20.{128+n}.0/24`, anycast gateway `.1`, workload addresses from `.10` |

Per tenant at index `n`, the API creates:

| Object | Derivation | `eds` (index 2) |
|--------|-----------|-----------------|
| EVPN zone, which **is** the VRF | the tenant's name | `eds`, `vrf-vxlan 10002` |
| VNet | `20000 + n×10` | `eds0`, tag `20020` |
| Subnet, with SNAT | `10.20.{128+n}.0/24` | `10.20.130.0/24` |

Proxmox caps SDN zone IDs at **8 characters**, and a zone ID is the tenant's name verbatim — which is
where the tenant name limit comes from. Workloads are addressed by cloud-init because Proxmox
implements SDN DHCP in Simple zones only, and a tenant's zone is an EVPN zone.

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
- ✅ dv02hyp002p02's bridge is VLAN-aware with `vmbr0.50` and `vmbr0.51` up, driven from inventory by the
  `proxmox_node_network` Ansible role.
- ✅ The fabric, VTEP identity and EVPN controller are applied on dv02hyp002p02 from
  `deevnet-tenant-fabric`. That repository holds hypervisor readiness only: the underlay, this
  node's VTEP identity and the EVPN controller. **A tenant's own zone, VNets, subnet and workloads
  are built by the Deevnet API**, declared from the tenant's own repository through the
  `deevnet/deevnet` provider
  ([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), deployed by
  [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/)).
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
  own exit-node behavior lets a VRF lookup fall through to the node's main table, which reaches
  the management segment on-link and unSNATed. The explicit default is what makes *every*
  non-connected destination leave via the perimeter.
