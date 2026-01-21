---
title: "Access Switch"
weight: 3
---

# Access Switch

## Purpose

The access switch provides **Layer 2 connectivity** for substrate hosts, connecting endpoints to the core router. Access switches handle VLAN tagging, port isolation, and traffic aggregation.

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│   Core Router   │◄────►│   Access Switch  │◄────►│  Substrate Hosts    │
│                 │      │                  │      │                     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```

---

## TP-Link Omada SG2218

**Substrate**: dvntm (mobile)

The SG2218 is a managed Gigabit switch from TP-Link's Omada SDN product line. It provides VLAN support and can be configured via SSH or the Omada controller.

### Hardware

| Attribute | Value |
|-----------|-------|
| **Model** | TP-Link Omada SG2218 |
| **Ports** | 16x Gigabit RJ45 |
| **Uplinks** | 2x SFP (1Gbps) |
| **Switching Capacity** | 36 Gbps |
| **MAC Table** | 8K entries |
| **Jumbo Frames** | 9216 bytes |
| **Power** | 8.65W max |
| **Dimensions** | 294 x 180 x 44mm |
| **Mounting** | Desktop or rack (1U) |

### Selection Rationale

- **VLAN support**: 802.1Q VLAN tagging for network segmentation
- **SSH access**: CLI configuration for automation
- **Omada SDN**: Centralized management via Omada controller
- **Compact**: Fits mobile substrate form factor
- **SFP uplinks**: Future 1G fiber connectivity option
- **Fanless**: Silent operation (passive cooling)

### Management

| Attribute | Value |
|-----------|-------|
| **Controller** | TP-Link Omada SDN |
| **CLI** | SSH access |
| **Web UI** | Standalone or controller-managed |
| **Automation** | Omada API via `deevnet.net` collection |

### Roles

| Role | Description |
|------|-------------|
| **L2 switching** | Connects substrate hosts to core router |
| **VLAN tagging** | 802.1Q trunk to core router |
| **Port isolation** | Separates trust zones at L2 |

---

## Ubiquiti UniFi USW-24-G2

**Substrate**: dvnt (home) — Primary switch

The USW-24-G2 is a 24-port managed Gigabit switch from Ubiquiti's UniFi product line. It serves as the primary access switch for the home substrate.

### Hardware

| Attribute | Value |
|-----------|-------|
| **Model** | Ubiquiti UniFi USW-24-G2 |
| **Ports** | 24x Gigabit RJ45 |
| **Uplinks** | 2x SFP (1Gbps) |
| **Switching Capacity** | 52 Gbps |
| **MAC Table** | 16K entries |
| **Power** | 17W max |
| **Dimensions** | 442 x 200 x 44mm |
| **Mounting** | Rackmount (1U) |
| **Cooling** | Fanless |

### Selection Rationale

- **Port density**: 24 ports for home infrastructure
- **UniFi ecosystem**: Centralized management via UniFi controller
- **VLAN support**: Full 802.1Q VLAN capabilities
- **Fanless**: Silent operation for home environment
- **SFP uplinks**: Fiber connectivity to core router (future)

### Management

| Attribute | Value |
|-----------|-------|
| **Controller** | UniFi Network Application |
| **CLI** | SSH access (limited) |
| **Web UI** | Controller-managed |
| **Automation** | UniFi API |

### Roles

| Role | Description |
|------|-------------|
| **L2 switching** | Primary switching for substrate hosts |
| **VLAN tagging** | 802.1Q trunk to core router |
| **Port profiles** | Per-port VLAN assignment |

---

## Ubiquiti UniFi US-8

**Substrate**: dvnt (home) — Secondary switch

The US-8 is an 8-port managed Gigabit switch used for expanding connectivity in areas away from the primary switch.

### Hardware

| Attribute | Value |
|-----------|-------|
| **Model** | Ubiquiti UniFi US-8 |
| **Ports** | 8x Gigabit RJ45 |
| **Switching Capacity** | 16 Gbps |
| **MAC Table** | 8K entries |
| **Power** | 5W max |
| **Dimensions** | 184 x 103 x 29mm |
| **Mounting** | Desktop |
| **Cooling** | Fanless |

### Selection Rationale

- **Compact**: Desktop form factor for distributed placement
- **UniFi ecosystem**: Managed by same controller as primary switch
- **Low power**: Efficient for always-on operation
- **VLAN support**: Extends VLANs to secondary locations

### Management

| Attribute | Value |
|-----------|-------|
| **Controller** | UniFi Network Application |
| **CLI** | SSH access (limited) |
| **Web UI** | Controller-managed |
| **Automation** | UniFi API |

### Roles

| Role | Description |
|------|-------------|
| **L2 switching** | Secondary switching for remote hosts |
| **VLAN tagging** | Extends VLANs from primary switch |
| **Uplink** | Connects to USW-24-G2 via trunk |

---

## Configuration Management

| Substrate | Controller | Automation |
|-----------|------------|------------|
| **dvntm** | Omada SDN | `deevnet.net` Ansible collection (Omada API) |
| **dvnt** | UniFi Network | UniFi API (manual currently) |

### VLAN Configuration

VLANs are defined in the substrate standards and configured on all access switches:

| VLAN | Purpose |
|------|---------|
| Management | Infrastructure management traffic |
| Tenant | Application/user traffic |
| IoT | Isolated IoT devices |

Specific VLAN IDs are documented in the [Network Segmentation](/docs/standards/network-segmentation/) standard.
