---
title: "Access Point"
weight: 4
---

# Access Point

## Purpose

The access point provides **wireless connectivity** for mobile devices, laptops, and IoT devices within the substrate.

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│  Access Switch  │◄────►│   Access Point   │◄────►│  Wireless Clients   │
│  (PoE + VLAN)   │      │   (Wi-Fi)        │      │                     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```

---

## TP-Link Omada EAP650-Outdoor

**Substrate**: dvntm (mobile)

The EAP650-Outdoor is a Wi-Fi 6 outdoor access point from TP-Link's Omada SDN product line. Despite being outdoor-rated, its rugged design makes it suitable for the mobile substrate's varied deployment environments.

### Hardware

| Attribute | Value |
|-----------|-------|
| **Model** | TP-Link Omada EAP650-Outdoor |
| **Wi-Fi Standard** | Wi-Fi 6 (802.11ax) |
| **Bands** | Dual-band (2.4GHz + 5GHz) |
| **Speed** | AX3000 (574 + 2402 Mbps) |
| **Antennas** | 2x2 internal (2.4GHz), 2x2 internal (5GHz) |
| **Ethernet** | 1x Gigabit RJ45 |
| **Power** | 802.3at PoE (12.3W typical) |
| **Weatherproofing** | IP67 |
| **Operating Temp** | -30°C to 70°C |
| **Mounting** | Wall/pole mount |

### Selection Rationale

- **VLAN capable**: Supports VLAN tagging per SSID for network segmentation
- **API manageable**: Omada controller provides REST API for automation
- **Wi-Fi 6**: Modern standard with improved efficiency and capacity
- **Rugged**: IP67 rating handles varied mobile deployment conditions
- **Omada ecosystem**: Matches dvntm switch (SG2218) for unified management
- **PoE powered**: Single cable for power and data

### Management

| Attribute | Value |
|-----------|-------|
| **Controller** | TP-Link Omada SDN |
| **VLAN Support** | Yes — per-SSID VLAN tagging |
| **API** | Yes — Omada controller REST API |
| **Automation** | `deevnet.net` Ansible collection (Omada API) |

### Roles

| Role | Description |
|------|-------------|
| **Wireless access** | Provides Wi-Fi 6 connectivity for clients |
| **SSID-to-VLAN mapping** | Multiple SSIDs mapped to VLANs |
| **Band steering** | Directs capable clients to 5GHz |

---

## Ubiquiti UniFi UAP-AC-M

**Substrate**: dvnt (home) — 2 units

The UAP-AC-M is a compact Wi-Fi 5 mesh-capable access point from Ubiquiti's UniFi product line. Two units provide coverage throughout the home substrate.

### Hardware

| Attribute | Value |
|-----------|-------|
| **Model** | Ubiquiti UniFi UAP-AC-M |
| **Wi-Fi Standard** | Wi-Fi 5 (802.11ac) |
| **Bands** | Dual-band (2.4GHz + 5GHz) |
| **Speed** | AC1200 (300 + 867 Mbps) |
| **Antennas** | 2x2 MIMO (external) |
| **Ethernet** | 1x Gigabit RJ45 |
| **Power** | 802.3af PoE (8.5W max) |
| **Weatherproofing** | Outdoor rated (IPX5) |
| **Mounting** | Wall/pole mount |
| **Mesh** | Wireless uplink capable |

### Selection Rationale

- **VLAN capable**: Supports VLAN tagging per SSID for network segmentation
- **API manageable**: UniFi controller provides REST API for automation
- **Mesh capable**: Wireless uplink for flexible placement
- **UniFi ecosystem**: Matches dvnt switches (USW-24-G2, US-8)
- **Compact**: Low-profile design for unobtrusive mounting
- **PoE powered**: Single cable for power and data

### Management

| Attribute | Value |
|-----------|-------|
| **Controller** | UniFi Network Application |
| **VLAN Support** | Yes — per-SSID VLAN tagging |
| **API** | Yes — UniFi controller REST API |
| **Automation** | UniFi API (manual currently) |

### Roles

| Role | Description |
|------|-------------|
| **Wireless access** | Provides Wi-Fi 5 connectivity for clients |
| **SSID-to-VLAN mapping** | Multiple SSIDs mapped to VLANs |
| **Mesh backhaul** | Wireless uplink between units (if needed) |

---

## VLAN and API Capability Summary

Both access points meet the core selection criteria:

| Requirement | EAP650-Outdoor (dvntm) | UAP-AC-M (dvnt) |
|-------------|------------------------|-----------------|
| **VLAN tagging** | ✓ Per-SSID | ✓ Per-SSID |
| **API management** | ✓ Omada REST API | ✓ UniFi REST API |
| **Controller-managed** | ✓ Omada SDN | ✓ UniFi Network |
| **PoE powered** | ✓ 802.3at | ✓ 802.3af |

---

## Configuration Management

| Substrate | Controller | Automation |
|-----------|------------|------------|
| **dvntm** | Omada SDN | `deevnet.net` Ansible collection (Omada API) |
| **dvnt** | UniFi Network | UniFi API (manual currently) |

### SSID Design

SSIDs are mapped to VLANs for network segmentation:

| SSID | VLAN | Purpose |
|------|------|---------|
| Management | Mgmt VLAN | Infrastructure access |
| IoT | IoT VLAN | IoT devices (isolated) |
| Guest | Guest VLAN | Visitor access (internet only) |

Specific VLAN IDs and SSID names are documented in the [Network Segmentation](/docs/standards/network-segmentation/) standard.
