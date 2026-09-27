---
title: "Edge Router"
weight: 1
---

# Edge Router

## Purpose

The edge router provides **upstream connectivity** between the site and the external network (ISP, travel router, or host network).

Edge routers are **external** to the site — they provide connectivity but are not managed by Deevnet automation. Configuration is manual or vendor-managed. The site assumes each edge router provides DHCP on its LAN interface (for bootstrap node or core router upstream connectivity).

{{< mermaid >}}
graph LR
    A[Edge Router<br>unmanaged] <--> B[Core Router<br>managed] <--> C[Site Hosts]
{{< /mermaid >}}

---

## Hardware

[GL-iNet GL-AXT1800 Slate AX](/docs/platforms/hardware/network/gl-inet-slate-ax/): specs, cabling, power and console.

---

## Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | OpenWrt |
| **Version** | [Software Catalog](/docs/platforms/software-catalog/#switching-wireless-and-edge) |
| **Base** | GL-iNet firmware (OpenWrt fork) |

## Roles

| Role | Description |
|------|-------------|
| **WAN connectivity** | Connects to upstream network (hotel, tether, etc.) |
| **NAT** | Masquerades substrate traffic |
| **DHCP** | Provides IP to core router WAN interface |
| **Wi-Fi repeater** | Extends upstream Wi-Fi to wired connection |

