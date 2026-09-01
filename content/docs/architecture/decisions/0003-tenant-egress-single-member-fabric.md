---
title: "ADR-0003: Tenant Egress on a Single-Member Fabric"
weight: 3
---

# ADR-0003: Tenant Egress on a Single-Member Fabric

|  |  |
|--|--|
| **Status** | **Accepted** |
| **Date** | 2026-09-01 |
| **Scope** | How tenant workloads reach the perimeter, and why they must reach it rather than route around it |
| **Depends on** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/) |

---

## Context

[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) chose a self-contained
EVPN/VXLAN fabric per tenant hypervisor, realized today as a **single-member fabric** on hv02 and
designed to expand by adding members. Seam 1 of that record defines north-south egress: aggregate
tenant traffic leaves the fabric on a transit VLAN, and the core router is a perimeter that never
learns tenant address space.

Phase 1 is built. Everything works except egress — and the investigation found **two independent
faults**, not one. They mask each other, and the more dangerous of the two is the one that looks
like success.

### What was already correct

Verified on `pve2`: fabric `tfab` (OpenFabric) with VTEP `10.20.255.2`; EVPN controller `evpn1`,
ASN 65020; tenant zone `tdemo` (VRF `vrf_tdemo`, VNI 10001); VNet `tdemo0` (VNI 20010) with anycast
gateway `10.20.129.1`; a cloud-init-addressed VM `tdemo-1` at `10.20.129.10/24`; the exit-node SNAT
rule; and hv02's own path to the internet via `10.20.50.1`.

Conntrack was correct throughout, holding the proper reverse tuple:

```
icmp 1 27 src=10.20.129.10 dst=8.8.8.8 type=8 id=32402
           src=8.8.8.8 dst=10.20.50.22 type=0 id=32402
```

### Fault 1 — the transit interface does not forward

Linux decides whether to forward a packet from the **ingress** interface's own forwarding flag.
Proxmox sets `ip-forward on` for the interfaces its SDN config owns — the VNet bridge, the underlay,
the VTEP loopback — so traffic *leaving* a tenant was always forwarded correctly.

The transit interface is not one of those. It is node substrate, declared in
`/etc/network/interfaces`, and the PVE network API has no forwarding property at all — its parser
also drops an `ip-forward` line written by hand. So it came up with `forwarding=0`:

```
vmbr0.50   forwarding=0     <- transit, node-owned
vmbr0.51   forwarding=1     <- underlay, redefined by the SDN generator
tdemo0     forwarding=1     <- VNet bridge, SDN-owned
```

The result is a one-way path that reads as a routing bug. Packet captures show echo requests leaving
`tdemo0`, being SNATed onto `vmbr0.50`, reaching the internet, **and being answered** — and the
kernel then refuses to forward the replies back in, because the interface they arrived on has
forwarding disabled. The VM sees 100% packet loss while the exit node's SNAT counter climbs.

That last detail matters, because a rising SNAT counter is exactly the evidence that invites the
conclusion that egress is working. It is not sufficient evidence; only traffic arriving inside the
VM is.

### Fault 2 — the VRF has no default route, and Proxmox's own answer bypasses the perimeter

Proxmox generates this for the exit node:

```
router bgp 65020 vrf vrf_tdemo
 address-family l2vpn evpn
  default-originate ipv4
  default-originate ipv6
 exit-address-family
exit
```

`default-originate` **advertises** a default to *other* VTEPs over EVPN. It installs nothing in the
exit node's own VRF. On a single-member fabric the only node *is* the exit node, there are no peers
(`% No BGP neighbors found in VRF default`), and the VRF holds only its connected route.

Proxmox does have an answer for this, in `PVE/Network/SDN/Zones/EvpnPlugin.pm`:

```perl
if (!$is_evpn_gateway) {
    push @iface_config, "post-up ip route add vrf $vrf unreachable default metric 4278198272";
} else {
    push @iface_config, "post-up ip route del vrf $vrf unreachable default metric 4278198272";
}
```

On an exit node it **deletes** the VRF's `unreachable default`, so a lookup that misses falls
through to the node's **main** routing table. Once forwarding is fixed, that does give a tenant the
internet.

It also breaks Seam 1. The main table contains the management segment, so a tenant's
management-bound traffic resolves on-link:

```
# ip route get 10.20.99.5 vrf vrf_tdemo      (fallthrough)
10.20.99.5 dev vmbr0 src 10.20.129.1
```

It leaves via the management bridge, unSNATed — the SNAT rule is `-o vmbr0.50` — and never passes
the perimeter. Captured on the management VLAN during the investigation:

```
IP 10.20.129.10 > 10.20.99.1:  ICMP echo request
IP 10.20.129.10 > 10.20.99.95: ICMP echo request
```

Raw tenant addresses on the management segment is precisely what ADR-0001 promised could not happen.
Return traffic is dropped by asymmetry rather than by policy, so TCP does not establish — but this
is a one-way injection path into the management plane, and it is not the perimeter that stops it.

### Why this is not a single-member workaround

The obvious remedy — a default route inside the VRF — was initially read as node-local state
propping up a fabric with too few members, in tension with ADR-0001 build requirement #2. That
reading was wrong on both counts.

It is **policy, not a crutch.** With an explicit default in the VRF, every destination the tenant is
not directly connected to leaves via the transit gateway:

```
# ip route get 10.20.99.5 vrf vrf_tdemo      (explicit default)
10.20.99.5 via 10.20.50.1 dev vmbr0.50 table vrf_tdemo src 10.20.129.1
```

**It does not go away at Phase 2.** In a multi-member fabric a VM on a non-exit node learns the
default over EVPN and tunnels to the exit node — where the traffic still has to leave the VRF. Without
the route the exit node still falls through to its main table, and the bypass returns. The gap does
not close by adding members; the earlier belief that it would was mistaken.

**It is supported configuration, not a patch.** `PVE/Network/SDN/Frr.pm` reads
`/etc/frr/frr.conf.local` and merges it into the generated config, and its parser folds a bare
`vrf <name>` stanza into the *existing* generated block rather than duplicating it. The claim that
the only published fix patches `BgpPlugin.pm`/`EvpnPlugin.pm` no longer holds on PVE 9.2.

---

## Decision

**Tenant egress is delivered as two node-local settings, both managed as code by the
`deevnet.net.proxmox_node_network` Ansible role under the `tenant-egress` tag.**

1. **IPv4 forwarding**, via `/etc/sysctl.d/90-deevnet-tenant-fabric.conf`:

   ```
   net.ipv4.conf.all.forwarding = 1
   net.ipv4.conf.default.forwarding = 1
   ```

   `default` covers interfaces created after boot, which is how the SDN's VRF and VNet devices
   appear; `all` covers those already up when sysctl runs.

2. **A default route inside each tenant VRF**, via `/etc/frr/frr.conf.local`:

   ```
   vrf vrf_tdemo
    ip route 0.0.0.0/0 10.20.50.1 nexthop-vrf default
   exit-vrf
   ```

   Proxmox merges this into its generated `frr.conf` on every SDN apply, so it lands inside
   Proxmox's own `vrf vrf_tdemo` stanza and survives `terraform apply`, `pvesh set /cluster/sdn`
   and reboot.

The tenant list is declared in inventory (`proxmox_tenant_egress.tenants`) rather than discovered.
The role fails if a declared tenant has no VRF on the node, so inventory and the tenant factory
cannot drift silently.

The role asserts the **routing outcome**, not the file write: that the transit interface forwards,
that each VRF holds a default via the transit gateway, and — the assertion that actually matters —
that management-bound tenant traffic resolves via the transit interface rather than the management
bridge.

IPv6 forwarding is deliberately left off. Tenants are IPv4-only today, and enabling it would open a
path with no corresponding policy.

## Consequences

**Egress works, and it works through the perimeter.** Measured after the change: `ping 8.8.8.8`
from `tdemo-1` at ~16 ms, HTTPS 200, DNS resolving; and **zero** tenant packets on the management
VLAN, against five in the same test before.

**Both settings are node-local state that Proxmox will not model.** This extends the bargain
already struck for the management source-based routing unit, for the same reason: the PVE network
API models interfaces and nothing else. ADR-0001 build requirement #2 is satisfied in substance —
nothing is hand-clicked or hand-carried, and a rebuilt node re-derives both from inventory — while
being technically outside the SDN object model. Requirement #2 should be read as *no hand-carried
node state*, not *no node state*.

**Adding a tenant now touches two repositories.** `terraform apply` creates the VRF; an Ansible run
with `--tags tenant-egress` gives it a way out. This is a real operational cost of declaring the
tenant list rather than discovering it, accepted in exchange for the routing being reviewable in
inventory. If it becomes friction, the alternative is to generate a stanza for every VRF found on
the node.

**A rising SNAT counter is not evidence of egress.** It was the basis of the original misdiagnosis.
Verification for tenant networking means traffic observed *inside the workload*.

**Phase 2 inherits this unchanged.** The exit node needs the leaked default however many members
the fabric has, so nothing here is removed when a second member joins — one less thing to unpick.

---

## Current state

- Both settings are applied on hv02 and code-managed; the earlier hand-added route is gone.
- Verified idempotent, and verified to survive a full `pvesh set /cluster/sdn`.
- The demo tenant `tdemo` (index 1, `10.20.129.0/24`) has working internet egress and no path onto
  the management VLAN.
