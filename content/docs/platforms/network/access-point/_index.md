---
title: "Access Point"
weight: 4
---

# Access Point

## Purpose

The access point provides **wireless connectivity** for mobile devices, laptops, and IoT devices within the substrate.

---

## Hardware

| Substrate | Hardware | Notes |
|-----------|----------|-------|
| **dvntm** | TBD | Compact AP for mobile deployment |
| **dvnt** | TBD | Ceiling-mount AP for home infrastructure |

### Selection Rationale

TBD — Selection criteria include:
- TP-Link Omada ecosystem compatibility
- Wi-Fi 6 or later support
- PoE powered (single cable deployment)
- Appropriate coverage for substrate physical layout

---

## Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | TP-Link Omada firmware |
| **Version** | TBD |

### Automation Capability

- Managed via **Omada Controller** (software-defined networking)
- Controller runs on bootstrap node
- Configuration is pushed from controller, not directly to AP
- Zero-touch provisioning when AP discovers controller

---

## Roles

| Role | Description |
|------|-------------|
| **Wireless access** | Provides Wi-Fi connectivity for clients |
| **SSID management** | Multiple SSIDs mapped to VLANs |
| **Client isolation** | Optional isolation between wireless clients |
| **Band steering** | Directs capable clients to 5GHz/6GHz |

---

## SSID Design

TBD — Future SSID configuration will include:

| SSID | VLAN | Purpose |
|------|------|---------|
| `deevnet-mgmt` | Management | Infrastructure access |
| `deevnet-iot` | IoT | IoT devices (isolated) |
| `deevnet-guest` | Guest | Visitor access (internet only) |

---

## Network Position

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│  Access Switch  │◄────►│   Access Point   │◄────►│  Wireless Clients   │
│  (PoE + VLAN)   │      │   (Wi-Fi)        │      │                     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```
