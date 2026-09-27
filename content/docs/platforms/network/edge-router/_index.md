---
title: "Edge Router"
weight: 1
---

# Edge Router

Fills the **edge router** role — see [Substrate Networking → Edge Router Role](/docs/architecture/substrate/networking/#edge-router-role).

It is not managed by Deevnet automation; configuration is manual, in the vendor UI.

| | |
|---|---|
| **Host** | `dv02edg001p01` |
| **WAN** | DHCP from whatever upstream is available |
| **LAN** | `192.168.8.0/24`, the travel router's own; the core router's WAN takes an address from it |

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

## Product features in use

| Feature | Use |
|---------|-----|
| **Wi-Fi repeater** | Joins an upstream Wi-Fi network and presents it as a wired WAN to the core router, so the site can attach to a hotel or a phone without a cable |

