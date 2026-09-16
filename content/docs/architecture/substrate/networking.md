---
title: "Networking"
weight: 1
---

# Substrate Networking Services

The substrate networking layer provides foundational network services for each site. The core router serves as the segment router, firewall, and service gateway for all segments within a substrate.

For the segment model (nine segment types, trust hierarchy, and routing policy), see [Network Segmentation](/docs/architecture/network-segmentation/).

---

## Core Router Role

Each substrate has a single core router that provides all networking services:

| Function | Description |
|----------|-------------|
| Segment routing | Inter-segment routing via VLAN interfaces |
| Firewall | Zone-based policy enforcement per segment |
| DNS | Authoritative for substrate zone, forwarding for external |
| DHCP | Static mappings for known hosts, dynamic pools per segment |
| NAT | Outbound gateway for all segments |
| Switching integration | VLAN trunking to access switch |
| Wireless integration | SSID-to-VLAN mapping via wireless AP |

---

## VLAN Routing

The core router maintains one interface per segment, each on its own VLAN:

- Each VLAN interface serves as the gateway (`.1`) for that segment's subnet
- Inter-segment traffic passes through the core router and is subject to firewall policy
- No direct layer-2 connectivity between segments — all cross-segment traffic is routed

---

## Firewall

The firewall enforces zone-based policy with each segment mapped to a firewall zone:

| Zone | Policy |
|------|--------|
| MGMT | Permissive outbound to all zones; restricted inbound |
| TRUSTED | Broad outbound access; restricted inbound |
| STOR | Highly restricted — only designated management and compute hosts |
| PLATFORM | Accepts inbound from management, trusted, workload transit, and IoT backend |
| TENANT | Perimeter for a **transit network** of workloads behind it; NAT, internet egress, and policy toward other zones — see note below |
| IOT | Outbound allowed; inbound restricted to IoT backend |
| IOT_VENDOR | Outbound internet only; no internal access |
| IOT_BACKEND | Accepts from IoT zone; outbound to platform |
| GUEST | Internet gateway only; no internal access |

The default policy is **deny all** — traffic between zones is blocked unless explicitly allowed.

The TENANT zone is a **perimeter only**. The networks behind its transit network are not substrate
segments, so the per-segment services below (VLAN routing, DHCP) don't apply to them. What sits
behind it is described in [Tenant Networking](/docs/architecture/tenant/networking/).

---

## DNS

The core router resolves for the substrate:

- Answers for the substrate zone (e.g. `mobile.deevnet.net`) from records generated out of inventory
- Forwards external queries to upstream resolvers
- Forwards zones it doesn't hold to the authoritative service that does, so their records never
  enter the resolver's own configuration

The full naming model, including why forwarding a zone is not the same as delegating it, is in
[Naming and Addressing](/docs/architecture/naming-and-addressing/).

---

## DHCP

Each segment has its own DHCP configuration on the core router:

- **Reservations** for every declared host, keyed on its hardware address and generated from
  inventory — this is how substrate hosts get their addresses, not local configuration
- **Dynamic pools** for segments with transient devices (trusted, IoT, guest), positioned above the
  reserved range so the two cannot collide
- **No dynamic pool** on the platform segment — everything on it is declared

Networks behind the TENANT perimeter are not addressed from here. See
[Naming and Addressing](/docs/architecture/naming-and-addressing/).

---

## NAT

The core router provides outbound NAT for all segments:

- All segments reach the internet through the core router's WAN interface
- Inbound NAT (port forwarding) is configured per-service as needed
- Guest and IoT Vendor segments are NAT-only with no internal routing

---

## Switching

The access switch connects all physical hosts to the core router:

- **Trunk ports** carry tagged traffic for all VLANs between the switch and core router
- **Access ports** assign hosts to their segment VLAN
- Multi-homed hosts may connect to multiple access ports on different VLANs
- **Native VLAN** on trunk ports is a dedicated blackhole VLAN (unrouted, no subnet) — untagged frames landing on a trunk are dropped into a dead VLAN rather than reaching a live network, preventing VLAN hopping and catching misconfigured devices

---

## Wireless

Wireless access is provided through APs connected to the access switch:

- Each SSID maps to a specific VLAN/segment
- Typical mappings: trusted SSID → trusted VLAN, guest SSID → guest VLAN, IoT SSID → IoT VLAN
- Wireless clients receive the same firewall policy as wired clients on the same segment
