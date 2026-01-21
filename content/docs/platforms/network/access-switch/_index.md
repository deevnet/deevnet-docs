---
title: "Access Switch"
weight: 3
---

# Access Switch

## Purpose

The access switch provides **Layer 2 connectivity** for substrate hosts, enabling VLAN segmentation and wired network access.

---

## Hardware

| Substrate | Hardware | Notes |
|-----------|----------|-------|
| **dvntm** | TBD | Compact managed switch for mobile deployment |
| **dvnt** | TBD | Rack-mounted managed switch for home infrastructure |

### Selection Rationale

TBD — Selection criteria include:
- Managed switch with VLAN support
- TP-Link Omada ecosystem compatibility (for unified management)
- Port count appropriate for substrate size
- PoE capability for access points and IoT devices

---

## Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | TP-Link Omada firmware |
| **Version** | TBD |

### Automation Capability

- Managed via **Omada Controller** (software-defined networking)
- Controller runs on bootstrap node
- Configuration is pushed from controller, not directly to switch
- No direct CLI/API automation — all management through Omada

---

## Roles

| Role | Description |
|------|-------------|
| **VLAN tagging** | Assigns ports to VLANs for network segmentation |
| **Port management** | Enables/disables ports, sets speed/duplex |
| **PoE delivery** | Powers access points and IoT devices |
| **Link aggregation** | Future: LAG for high-bandwidth connections |

---

## VLAN Design

TBD — Future VLAN segmentation will include:

| VLAN | Purpose |
|------|---------|
| Management | Substrate infrastructure (hypervisors, bootstrap) |
| Tenant | Tenant workloads |
| IoT | Isolated segment for IoT devices |

---

## Network Position

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│  Core Router    │◄────►│  Access Switch   │◄────►│  Substrate Hosts    │
│  (gateway)      │      │  (L2 switching)  │      │  (wired devices)    │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```
