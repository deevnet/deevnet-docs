---
title: "ADR-0003: Tenant Egress on a Single-Member Fabric"
weight: 3
---

# ADR-0003: Tenant Egress on a Single-Member Fabric

|  |  |
|--|--|
| **Status** | **Proposed — problem stated, not yet decided** |
| **Date** | 2026-09-01 |
| **Scope** | How tenant workloads reach the perimeter while the fabric has exactly one member |
| **Depends on** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/) |

---

## Context

[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) chose a self-contained
EVPN/VXLAN fabric per tenant hypervisor, realized today as a **single-member fabric** on hv02 and
designed to expand by adding members. Seam 1 of that record defines north-south egress: aggregate
tenant traffic leaves the fabric on a transit VLAN, and the core router is a perimeter that never
learns tenant address space.

Phase 1 is now built and every part of that model works **except egress**.

### What works

Verified on `pve2`:

| Element | State |
|---------|-------|
| Fabric `tfab` (OpenFabric), VTEP `10.20.255.2` on `dummy_tfab` | up |
| EVPN controller `evpn1`, ASN 65020 | up |
| Tenant zone `tdemo` — VRF `vrf_tdemo`, VNI 10001 | up |
| VNet `tdemo0` (VNI 20010), anycast gateway `10.20.129.1` | up |
| Tenant VM, addressed and named by cloud-init | `tdemo-1` at `10.20.129.10/24` |
| Routing inside the VRF | VM reachable from `ip vrf exec vrf_tdemo` |
| SNAT at the exit node | `-s 10.20.129.0/24 -o vmbr0.50 --to-source 10.20.50.22` |
| Perimeter transit | hv02 reaches the internet via `10.20.50.1`, ~14 ms |

So the fabric, the numbering, the addressing pipeline, the exit-node SNAT and the perimeter are all
in place and correct.

### The problem

**A tenant VM has no route out.** The zone VRF contains only its connected route:

```
# ip route show vrf vrf_tdemo
10.20.129.0/24 dev tdemo0 proto kernel scope link src 10.20.129.1
```

There is no default route, so tenant traffic is dropped at the exit node.

This is not a misconfiguration. It is what Proxmox generates. The exit-node stanza in
`/etc/frr/frr.conf` is:

```
router bgp 65020 vrf vrf_tdemo
 address-family l2vpn evpn
  default-originate ipv4
  default-originate ipv6
 exit-address-family
exit
```

`default-originate` **advertises** a default route to *other* VTEPs over EVPN. It does not install
one in the exit node's own VRF. In a multi-member fabric that is correct and sufficient: VMs live
on non-exit nodes, learn the default from the exit node, and tunnel to it. In a **single-member**
fabric the only node *is* the exit node, there are no peers to advertise to, and a VM on that node
gets nothing.

```
# vtysh -c "show bgp summary"
% No BGP neighbors found in VRF default
```

Which is expected with one member — and is precisely why the mechanism cannot fire.

### What has been ruled out

Established during Phase 1 build-out, so the next discussion need not repeat it:

- **`exitnodes-local-routing`** does not address this. It was enabled and changed nothing. Its
  documented purpose is reaching a VM's services *from* an exit node, not giving a VM egress.
- **No zone option covers it.** The full EVPN zone option set (`exitnodes`,
  `exitnodes-local-routing`, `exitnodes-primary`, `rt-import`, `advertise-subnets`, …) contains
  nothing that leaks a default route into the VRF.
- **The perimeter is not at fault.** hv02 reaches the internet over the transit VLAN, so the
  transit segment, its outbound NAT and the core router are all working.
- **The mechanism is understood, not merely suspected.** Adding a leaked default by hand —
  `ip route add default via 10.20.50.1 dev vmbr0.50 vrf vrf_tdemo` — immediately caused the
  exit-node SNAT counter to increment from zero, confirming traffic then leaves the VRF, is
  translated to the transit address, and egresses as designed.
- **The one published fix patches Proxmox itself** (`BgpPlugin.pm` / `EvpnPlugin.pm`), which is a
  feature request rather than supported configuration.

### Why this is awkward

The obvious remedy is a leaked default route in the VRF. That is **node-local state Proxmox will
not manage**, which runs against ADR-0001 build requirement #2 — *SDN-as-code, no hand-carried node
state* — the discipline that keeps "cluster later" a re-apply rather than a migration.

There is partial precedent: the management interface already carries a source-based routing systemd
unit that Proxmox does not model, delivered as code through the `proxmox_node_network` Ansible role.
Whether that precedent should extend to the tenant data plane is exactly the question.

There is also a legitimate position that this needs no fix at all: the gap closes on its own when
the fabric gains a second member, since a VM would then sit on a non-exit node and learn the default
over EVPN as designed. That trades Phase 1 tenant egress for architectural purity, and Phase 2 is
currently unscheduled.

---

## Decision

**Not yet taken.** This record exists to state the problem; the options have not been evaluated.

## Consequences

To be completed once a decision is made.

---

## Current state

For whoever picks this up:

- A leaked default route is **live on hv02 but not persistent** — it was added by hand to confirm
  the diagnosis and will disappear on the next network reload. Nothing in code creates it.
- The demo tenant `tdemo` (index 1, `10.20.129.0/24`) is applied and running, and is disposable.
- Everything else described above is code-managed in `deevnet-tenant-factory` and the
  `deevnet.net` Ansible collection.
