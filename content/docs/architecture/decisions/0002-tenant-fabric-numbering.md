---
title: "ADR-0002: Tenant Fabric Numbering"
weight: 2
---

# ADR-0002: Tenant Fabric Numbering

|  |  |
|--|--|
| **Status** | Accepted |
| **Date** | 2026-08-30 |
| **Scope** | Address and identifier allocation for the tenant fabric and the tenants on it |
| **Depends on** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/) |

---

## Context

ADR-0001 made **globally-unique numbering** its first build requirement: allocate VNIs, VRF
identifiers, and tenant subnets *as if they already share one fabric*, so that gaining a member
is additive rather than a renumbering. It did not say what that scheme is. The Tenant Platform
roadmap carried it as an open thread.

The scheme has to answer three questions the existing addressing plan cannot:

1. **Where do tenant subnets live?** The substrate convention is `10.{site}.{vlan_id}.0/24`, with
   the third octet carrying the VLAN ID. A tenant overlay is *not* a VLAN, so that convention
   cannot describe it.
2. **What replaces the tenant VLAN band?** VLANs 50–59 were reserved for "tenant segments" under
   the model ADR-0001 superseded. Tenants no longer have VLANs at all.
3. **Where does the underlay live?** Requirement #4 calls for a real VTEP identity now. Loopbacks
   are infrastructure, not tenant space.

---

## Decision

### Split the site `/16` rather than opening a second one

| Block | Purpose |
|-------|---------|
| `10.20.0.0/17` | Substrate segments — third octet = VLAN ID. Unchanged. |
| `10.20.128.0/18` | **Tenant overlay subnets** — `10.20.{128+n}.0/24` per tenant, `n` = 1–63 |
| `10.20.255.0/24` | **Fabric loopbacks / VTEP identity** — `pve2` = `10.20.255.2` |

home mirrors this in `10.10.0.0/16`.

The alternative was a separate `/16` per site for overlays. Splitting the existing block is
better for one concrete operational reason: it keeps **exactly one aggregate per site**. In home
dock mode, home already routes `10.20.0.0/16` to mobile, and that single route keeps covering
tenants for free. A second `/16` would need its own route, at every point that already carries
the first.

### Repurpose VLANs 50/51 as tenant fabric transport

The 50–59 band is redefined from "tenant segments" to **tenant fabric transport** — still
tenant-related, but transport for the fabric rather than a network per tenant.

| VLAN | Name | Subnet | Router IP |
|------|------|--------|-----------|
| 50 | `tenant_transit` | `10.20.50.0/24` | `.1` — the perimeter handoff |
| 51 | `tenant_underlay` | `10.20.51.0/24` | **none** — VTEP-to-VTEP transport only |

`tenant_1/2/3` (VLANs 50/51/52) are deleted. The IDs are reused rather than retired because they
never carried traffic — the tenant hypervisor was never trunked under the old model.

`tenant_underlay` is recorded with **no subnet and no gateway** in the substrate VLAN table, the
same shape as the blackhole VLAN. The core router neither routes it nor holds an address on it,
so listing it as a substrate segment would overstate what it is. Its addressing belongs to the
fabric.

### Derive every identifier from one number

A tenant is allocated a single **`tenant_index`** (`n`). Everything else follows:

| Identifier | Formula (mobile) | `n = 1` |
|------------|-----------------|---------|
| VRF VXLAN — *the EVPN zone* | `10000 + n` | 10001 |
| VNet VNI, `i`th vnet | `20000 + n*10 + i` | 20010 |
| Overlay subnet | `10.20.{128+n}.0/24` | 10.20.129.0/24 |
| Anycast gateway | `.1` of that subnet | 10.20.129.1 |
| Workload addresses | `.10` upward, by index | 10.20.129.10, .11, … |
| BGP ASN (per site) | 65020 mobile / 65010 home | 65020 |

home uses bases `11000` and `21000`, so identifiers stay distinct across sites as well as across
fabric members.

> **Amended 2026-09-01.** This table originally reserved a fabric DHCP range of `.100`–`.200`.
> Proxmox implements SDN DHCP in the *Simple* zone plugin only — EVPN zones have none, and the API
> rejects the attribute outright. Workloads are addressed by cloud-init instead, derived from the
> tenant index rather than leased, which also matches the deterministic addressing the rest of the
> estate uses. `.2`–`.9` stay reserved for future fabric use.

One number per tenant is the point. It removes the opportunity to hand-assign a VNI that happens
to be free *today* on *this* node and collides the moment the fabric gains a member — which is
the failure requirement #1 exists to prevent.

**Allocation is recorded in `TENANTS.md` in the tenant factory**, in the same change that adds the
tenant. An index is never reused while its tenant exists.

### Naming constraint

Proxmox limits SDN zone and VNet IDs to **8 characters**, and the zone ID is the tenant name
verbatim. Tenant names must fit.

---

## Consequences

### Positive

- A tenant's entire numbering follows from one allocation, so collisions are a registry problem
  rather than a design problem.
- One routable aggregate per site; no new routes anywhere to reach tenant space.
- Substrate and tenant space are distinguishable from the address alone — below `.128` in the
  third octet is substrate, at or above is a tenant overlay.

### Negative / accepted

- 63 tenants per site. Far beyond what this estate will hold, and the `/18` can be widened without
  disturbing anything already allocated.
- The 50–59 band now means something different from what `architecture/addressing.md` originally
  reserved it for. That document is updated to match rather than left to contradict this.

### Neutral

- Tenant subnets are not routed off the hypervisor today: subnets carry SNAT, so the exit node
  translates tenant traffic to its transit address and the core router never learns tenant space.
  The plan is still built to be routable, so that per-VRF exit (ADR-0001 seam 1) remains available
  without renumbering.
