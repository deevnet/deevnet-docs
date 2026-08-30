---
title: "ADR-0001: Tenant Network Fabric"
weight: 1
---

# ADR-0001: Tenant Network Fabric

|  |  |
|--|--|
| **Status** | Accepted |
| **Date** | 2026-08-30 |
| **Scope** | Tenant networking on the tenant hypervisor; relationship to the core router and management hypervisor |
| **Supersedes** | The Option A tenant-networking model previously described in `architecture/tenant/networking.md` (core-router-owned per-tenant VLANs) |

---

## Context

We are ready to begin hosting **tenants** — isolated application workloads — on the tenant
hypervisor. A tenant needs a network: an address space, a gateway, routing, isolation from
other tenants, and a controlled path to the outside world.

The question this record answers is **where the tenant's Layer 3 lives** — because that one
choice determines everything downstream (who owns the gateway, where isolation is enforced,
what the switch has to know, and how a tenant is rebuilt from code).

### Goals that forced the choice

1. **Learning-first.** The Deevnet platform exists to learn and implement cloud-style
   infrastructure patterns properly, not to reach the shortest path to a running VM.
2. **Separation of physical and virtual.** Tenant networks should be virtual constructs that
   do not require hand-editing physical switch configuration every time a tenant is created.
3. **Code is the source of truth.** Every tenant must supply the IaC and CaC needed to rebuild
   itself from scratch against the Deevnet substrate. Network definitions are code, not
   hand-clicked state.
4. **Expandable.** Start on a single tenant hypervisor, but design so the tenant compute layer
   can grow into a cluster later **without redefining the model or tearing anything out.**

### Relevant existing doctrine

- The core router (OPNsense) is currently the single L3 authority for all substrate segments.
- Both hypervisors are documented as **non-clustered, independent, stateless, locally-stored** —
  clustering was previously rejected to avoid two-node quorum fragility.
- The two hypervisors serve **different purposes** and are intentionally separated:
  - **hv01 — management hypervisor.** Runs the management plane: monitoring, observability,
    automation, and the tooling that manages the *physical* side of the infrastructure. It may
    grow into its own cluster in the future, but for a distinct purpose and on its own path.
  - **hv02 — tenant hypervisor.** Hosts tenant application workloads. This ADR governs its
    networking. The two hypervisors are not joined into one cluster; each evolves independently.

---

## Decision drivers

| Driver | Effect on the choice |
|--------|----------------------|
| Physical/virtual separation | Rules out any model that needs a switch change per tenant |
| Code as source of truth | Network must be declarative and rebuildable; no precious node state |
| Learning payload | Favors the "real" cloud model (routed overlay) over the shortest path |
| Expandable to a cluster | Favors a paradigm that *adds* nodes rather than being *replaced* to scale |
| Plane separation (mgmt vs tenant) | Favors keeping the tenant network invisible to the management hypervisor |
| Avoid premature quorum cost | Favors staying standalone now, not clustering to "get ahead" |

---

## Options considered

### Option A — Core-router-owned tenant VLANs

Each tenant is a physical VLAN. The tenant hypervisor only tags a VM's virtual NIC onto that
VLAN (via a VLAN-aware bridge or a Proxmox SDN *VLAN zone*); the core router owns the gateway,
DHCP, and firewall for every tenant.

- **Pros:** Simplest. Reuses the existing core-router authority model unchanged.
- **Cons:** Every virtual tenant is handcuffed to a **physical** VLAN — the switch port must be
  trunked and the core router reconfigured for each new tenant. This is the *opposite* of
  physical/virtual separation. No meaningful learning payload. It is also the current source of
  operational friction (per-tenant switch edits, currently manual due to stale switch creds).
- **Verdict:** Rejected. Directly contradicts goals 1 and 2.

### Option B1 — Shared clustered overlay fabric (cluster hv01 + hv02 now)

Join both hypervisors into one Proxmox cluster and define a single, cluster-wide EVPN/VXLAN
SDN fabric. Tenants can span nodes; live migration is possible.

- **Pros:** "Real datacenter" from day one; a tenant network can stretch across nodes.
- **Cons:** Breaks the established non-clustered doctrine. Introduces two-node **quorum
  fragility** (needs a third vote / QDevice). Couples the management plane and the tenant plane
  into one control and failure domain — the exact opposite of the intended plane separation.
- **Verdict:** Rejected. Pays cluster complexity now for benefits not yet needed, and couples two
  planes that must stay independent.

### Option B2 — Self-contained overlay fabric per tenant hypervisor *(chosen)*

Each tenant hypervisor runs its **own** EVPN/VXLAN SDN fabric, entirely local to the node. The
tenant compute domain owns the tenant's Layer 3: a routed overlay with an anycast gateway,
one VRF per tenant for isolation, and its own IPAM. The core router drops back to a
**perimeter-only** role. The fabric currently has exactly one member (hv02) but is modeled as a
fabric so additional members can join later.

- **Pros:** Cleanest expression of every goal — virtual tenant networks with no per-tenant
  switch change; the whole network is declarative code that rebuilds a node whole; the tenant
  plane is invisible to the management hypervisor; and scaling is *additive*.
- **Cons:** A tenant lives on one hypervisor; no cross-node tenants or live migration until/unless
  a cluster is formed. On a single node the overlay encapsulation is **pedagogical** — it teaches
  the model and sets up the pattern, but carries no inter-node transport yet.
- **Verdict:** **Accepted.** The costs are constraints we had already accepted (VMs don't
  auto-migrate; local storage only), and the trajectory is designed in rather than bolted on.

### The starter trap (why we do *not* "start simple")

The simplest starting points — a VLAN-aware bridge, or plain VXLAN without an EVPN control plane —
are a **different paradigm** (no distributed control plane, no anycast gateway, no VRF model). If
we started there to "get going," reaching a cluster later would mean tearing that out and
rebuilding. Doing EVPN properly now is therefore *both* the learning-correct and the
future-proof choice: single-member fabric → multi-member fabric is "add peers," not "replace the
model." The two goals point at the same decision.

---

## Decision

Adopt **Option B2: a self-contained EVPN/VXLAN overlay fabric per tenant hypervisor**, realized
today as a **single-member fabric** on hv02 and designed to expand into a clustered fabric
without redefinition.

This relocates tenant Layer 3 from the core router into the tenant compute domain and redefines
the core router's tenant role as a **perimeter**.

### Seam 1 — The north-south handoff (perimeter transit)

The routed overlay exits to the core router over a dedicated **transit network**: a single
transit segment carrying *aggregate* tenant egress from the hypervisor to the core router. The
core router no longer sees individual tenant subnets — only the transit network — and provides
NAT, internet egress, and tenant↔management policy at that boundary.

- **Phase 1 choice:** a **single transit VLAN** per hypervisor. Minimum that preserves
  self-containment and gives the core router a clean perimeter role. North-south isolation
  between tenants is enforced inside the fabric (VRFs).
- **Future option:** per-VRF exit (separate transit segments per tenant) if the core router ever
  needs to enforce per-tenant egress policy. Generalizes the same seam; not needed now.

### Seam 2 — IPAM / DHCP / DNS ownership

- **IPAM and DHCP** are owned by the tenant fabric (SDN IPAM + per-VNet DHCP). The core router
  never learns tenant address space — a cleaner separation than the previous model.
- **DNS** is split by ownership: internal tenant records are owned by the tenant and **published
  into the substrate zone** so `service.tenant.site.deevnet.net` continues to resolve.

### Four disciplines that keep the cluster door open

These are **build requirements**, not preferences — violating any one reintroduces lock-in:

1. **Globally-unique numbering.** Allocate VNIs, VRF identifiers, and tenant subnets as if they
   already share one fabric. No "locally-meaningful-only" identifiers.
2. **SDN-as-code from line one.** No hand-clicked SDN objects. This is what converts "cluster
   later" from a migration into a re-apply at cluster scope.
3. **EVPN from the start**, not a VLAN-aware bridge or plain VXLAN — keep the control-plane
   paradigm constant so scaling is additive.
4. **A real underlay/VTEP identity now.** Give the lone node a proper loopback/VTEP address and
   an underlay concept even with no peers, so adding a member is "add a neighbor," not "invent an
   underlay after the fact."

---

## Consequences

### Positive

- Tenant networks are pure virtual constructs; creating a tenant requires **no switch change**.
- The entire tenant network is declarative code; rebuilding a tenant hypervisor reconstitutes its
  fabric whole, with no peer to reconcile against.
- The management hypervisor has zero knowledge of tenant overlays — clean plane separation.
- The path to a tenant cluster is additive: nothing structural is torn out to scale.

### Negative / accepted costs

- No cross-node tenants and no live migration until a cluster is formed (already-accepted).
- On a single node the overlay encapsulation carries no inter-node traffic yet — its value now is
  the model and the learning, not transport.
- The core router's tenant role changes; substrate networking docs that describe per-tenant VLAN
  interfaces and per-tenant DHCP on the core router are superseded for tenants.

### Neutral

- Forming a cluster later brings quorum management (a QDevice as a third vote). This cost is taken
  on **only** when multi-node is actually wanted; it does not affect the single-node build.

---

## Trajectory

| Aspect | Phase 1 — single-member fabric (now) | Phase 2 — tenant cluster (future) |
|--------|--------------------------------------|-----------------------------------|
| Proxmox topology | hv02 standalone | hv02 + additional tenant nodes clustered, QDevice for quorum |
| SDN paradigm | EVPN zone, VRF-per-tenant | **Identical** — same objects, cluster-scoped |
| Anycast gateway | Present, on hv02 | **Same**, now distributed across nodes |
| Underlay | VTEP identity defined, no peers | Peers added; neighbors formed |
| Tenant IaC | Targets hv02's fabric | **Unchanged** — targets the fabric |
| Transit seam → core router | hv02's transit VLAN | Fabric exit node(s) → core router (same seam, generalized) |
| What is rebuilt to scale | — | **Nothing structural** — members are added |

The management hypervisor (hv01) follows a **separate** trajectory: it too may grow into its own
cluster, but for the management plane and independently of the tenant fabric. The two planes do
not merge.

---

## Status of implementation

**Documentation only. No code has been written.** This record and the accompanying architecture,
platform, and roadmap pages establish the design; implementation is tracked as a roadmap project
and begins only after this design is settled.
