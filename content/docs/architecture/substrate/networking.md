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
| PLATFORM | Accepts inbound from management, trusted, tenant, and IoT backend |
| TENANT | Per-tenant rules; access to platform services via explicit allow |
| IOT | Outbound allowed; inbound restricted to IoT backend |
| IOT_VENDOR | Outbound internet only; no internal access |
| IOT_BACKEND | Accepts from IoT zone; outbound to platform |
| GUEST | Internet gateway only; no internal access |

The default policy is **deny all** — traffic between zones is blocked unless explicitly allowed.

---

## DNS

The core router provides DNS for the substrate:

- **Authoritative** for the substrate zone (e.g., `dvntm.deevnet.net`)
- **Forwarding** for external queries to upstream resolvers
- Static records for infrastructure hosts; dynamic registration where supported

---

## DHCP

Each segment has its own DHCP configuration on the core router:

- **Static mappings** for known infrastructure hosts (routers, hypervisors, switches, APs)
- **Dynamic pools** for segments with transient devices (trusted, IoT, guest)
- **No dynamic DHCP** on management and platform segments — static only

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
