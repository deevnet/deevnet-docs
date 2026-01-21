---
title: "Raspberry PIs"
weight: 2
bookCollapseSection: true
---

# Raspberry PIs

## Purpose

Raspberry PIs provide **edge and IoT compute** for specialized workloads that benefit from small form factor, low power consumption, or dedicated hardware interfaces.

---

## Hardware

| Substrate | Hardware | Notes |
|-----------|----------|-------|
| **dvntm** | TBD | Portable Pi deployment |
| **dvnt** | 4x Raspberry PI | IoT segment placement |

### Selection Rationale

TBD — Selection criteria include:
- Raspberry Pi 4 or 5 models
- Sufficient RAM for workload requirements
- GPIO/interface capabilities for specific use cases
- PoE HAT support for single-cable deployment

---

## Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | TBD |
| **Version** | TBD |
| **Base** | Raspberry Pi OS or Fedora ARM |

### Automation Capability

- **Image provisioning**: deevnet-image-factory builds Pi images
- **cloud-init**: Supported for initial configuration
- **Ansible**: Post-boot configuration via `deevnet.builder`
- **PXE boot**: Pi 4+ supports network boot (UEFI)

---

## Roles

TBD — Potential roles include:

| Role | Description |
|------|-------------|
| **SDR gateway** | Software-defined radio signal processing |
| **Sensor collection** | IoT sensor aggregation |
| **Local processing** | Edge compute for latency-sensitive tasks |
| **Display/kiosk** | Information displays |

---

## Network Position

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│  Core Router    │◄────►│  Access Switch   │◄────►│  Raspberry PIs      │
│                 │      │  (IoT VLAN)      │      │  (edge compute)     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```

Raspberry PIs are placed on the IoT network segment for isolation from management and tenant workloads.

---

## Image Factory Integration

Pi images are built via the **deevnet-image-factory** repository:

1. **Base image**: Raspberry Pi OS or Fedora ARM
2. **cloud-init**: Pre-configured for substrate connectivity
3. **a_autoprov user**: Provisioned for Ansible access
4. **Artifact staging**: Images stored on artifact server

---

## Future Development

| Feature | Status |
|---------|--------|
| Network boot | TBD |
| Automated SD card imaging | TBD |
| Role-specific images | TBD |
| Fleet management | TBD |
