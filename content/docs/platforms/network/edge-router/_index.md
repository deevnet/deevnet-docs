---
title: "Edge Router"
weight: 1
---

# Edge Router

## Purpose

The edge router provides **upstream connectivity** between the substrate and the external network (ISP, travel router, or host network).

Edge routers are **external** to the substrate — they provide connectivity but are not managed by Deevnet automation. Configuration is manual or vendor-managed. The substrate assumes each edge router provides DHCP on its LAN interface (for bootstrap node or core router upstream connectivity).

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│   Edge Router   │◄────►│   Core Router    │◄────►│  Substrate Hosts    │
│   (unmanaged)   │      │   (managed)      │      │                     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```

---

## GL-iNet GL-AXT1800 (Slate AX)

**Substrate**: dvntm (mobile)

The GL-AXT1800 Slate AX is a portable Wi-Fi 6 travel router used as the edge router for the mobile substrate. It provides upstream connectivity when traveling — connecting to hotel Wi-Fi, tethered phones, or any available network.

### Hardware

| Attribute | Value |
|-----------|-------|
| **Model** | GL-iNet GL-AXT1800 (Slate AX) |
| **CPU** | IPQ6000 1.2GHz quad-core |
| **Memory** | 512MB DDR3L |
| **Storage** | 128MB NAND Flash |
| **Ethernet** | 3x Gigabit (1 WAN, 2 LAN) |
| **Wi-Fi** | Wi-Fi 6 (802.11ax) dual-band, 1800Mbps |
| **USB** | USB 3.0 |
| **Power** | USB-C, <8.75W max |
| **Dimensions** | 125 x 82 x 36mm |
| **Weight** | 245g |

### Selection Rationale

- **Portability**: Compact form factor with retractable antennas fits in a laptop bag
- **Flexible upstream**: Can connect via Ethernet, Wi-Fi repeater, or USB tethering
- **OpenWrt-based**: Runs standard OpenWrt with full package ecosystem
- **VPN capable**: WireGuard and OpenVPN at near-gigabit speeds
- **Power efficient**: Runs from USB-C power bank if needed

### Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | OpenWrt |
| **Version** | 23.05-SNAPSHOT |
| **Base** | GL-iNet firmware (OpenWrt fork) |

### Roles

| Role | Description |
|------|-------------|
| **WAN connectivity** | Connects to upstream network (hotel, tether, etc.) |
| **NAT** | Masquerades substrate traffic |
| **DHCP** | Provides IP to core router WAN interface |
| **Wi-Fi repeater** | Extends upstream Wi-Fi to wired connection |

---

## AT&T Fiber BGW320

**Substrate**: dvnt (home) — Primary connection

The BGW320 is AT&T's fiber gateway combining an ONT (Optical Network Terminal) and router in one unit. It provides the primary internet connection for the home substrate.

### Hardware

| Attribute | Value |
|-----------|-------|
| **Model** | AT&T BGW320-505 |
| **Type** | XGS-PON Broadband Gateway with integrated ONT |
| **Ethernet** | 1x 5Gbps + 3x Gigabit |
| **Wi-Fi** | Wi-Fi 6 (802.11ax), AX3600 class |
| **Phone** | Analog phone port (VoIP) |
| **USB** | USB 2.0 |

### Selection Rationale

- **ISP-provided**: Required for AT&T Fiber service
- **Integrated ONT**: Fiber terminates directly in the gateway
- **5Gbps port**: Supports multi-gig speeds for future upgrades
- **IP Passthrough**: Can pass public IP to core router

### Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | AT&T firmware (proprietary) |
| **Version** | Vendor-managed |
| **Base** | Proprietary |

### Configuration

The BGW320 is configured for **IP Passthrough** mode:
- Public IP is passed through to the core router
- BGW320 handles fiber termination only
- Core router manages all routing, firewall, and NAT

### Roles

| Role | Description |
|------|-------------|
| **Fiber termination** | ONT converts fiber to Ethernet |
| **IP Passthrough** | Passes public IP to core router |
| **DHCP** | Provides IP to core router WAN interface |

---

## Spectrum Internet

**Substrate**: dvnt (home) — Secondary connection (failover)

Spectrum provides the secondary internet connection for WAN failover. This connection is **not yet implemented** but planned for redundancy.

### Hardware

| Attribute | Value |
|-----------|-------|
| **Model** | TBD (Spectrum-provided or DOCSIS 3.1 modem) |
| **Type** | Cable modem (DOCSIS) |
| **Ethernet** | Gigabit |

### Selection Rationale

- **Redundancy**: Different last-mile technology (cable vs fiber) for true failover
- **Different provider**: Avoids single-provider outage scenarios
- **Cost-effective**: Basic tier sufficient for failover purposes

### Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | Spectrum firmware or DOCSIS modem firmware |
| **Version** | Vendor-managed |

### Implementation Status

| Component | Status |
|-----------|--------|
| Physical connection | TBD |
| Modem provisioning | TBD |
| Core router dual-WAN | TBD |
| Failover automation | TBD |

### Planned Roles

| Role | Description |
|------|-------------|
| **WAN connectivity** | Secondary internet path |
| **DHCP** | Provides IP to core router secondary WAN |
| **Failover** | Automatic switchover when primary fails |
