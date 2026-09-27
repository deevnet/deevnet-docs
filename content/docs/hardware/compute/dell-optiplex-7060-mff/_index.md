---
title: "Dell OptiPlex 7060 Micro"
weight: 3
bookCollapseSection: true
---

# Dell OptiPlex 7060 Micro

The tenant hypervisor. A near-twin of the
[OptiPlex 7050 Micro](../dell-optiplex-7050-mff/), one generation newer, with the same single Intel
NIC and the same 32GB. What differs:

| | 7050 Micro (management) | **7060 Micro (tenant)** |
|---|---|---|
| **CPU** | i7-6700T, 4-core/8-thread | **i5-8600T, 6-core/6-thread** (2.3-3.7GHz, 35W TDP) |
| **Memory** | 32GB DDR4 | **32GB DDR4 (2x 16GB)** |
| **OS disk** | 512GB M.2 SATA SSD | **512GB SATA SSD (SK hynix SC311)** |
| **Data disk** | 2TB SATA SSD | **2TB SATA SSD (Crucial BX500)** |
| **NIC name** | `enp0s31f6` | **`eno2`** (Intel I219-LM) |
| **Wi-Fi** | none | **Intel CNVi. Present, not used** |

## Selection Rationale

The same reasons as the [7050 Micro](../dell-optiplex-7050-mff/#selection-rationale): a
repurposed enterprise desktop, 32GB for many VMs, compact, low-power, and Intel VT-x/VT-d.

## In Service

| Host | Role |
|---|---|
| `dv02hyp002p02` | [Tenant Hypervisor](/docs/platforms/tenant-compute/tenant-hypervisors/) |

## Physical

| NIC | Connects to |
|---|---|
| `eno2` | Switch `gi1/0/13`, trunk, native VLAN 99, VLANs 50 and 51 tagged (the tenant fabric) |

- **Single NIC:** as on the 7050.
- **Wake-on-LAN:** enabled.
- **Console:** as on the 7050; see
  [Hypervisor console recovery](/docs/runbook/substrate/recovery/console-recovery/hypervisor/).

## Firmware

The BIOS version is in the
[Software Catalog](/docs/platforms/software-catalog/#tenant-hypervisor-dv02hyp002p02).

## Certification

| | |
|---|---|
| **Role** | Tenant hypervisor |
| **Current** | {{< status-badge "planned" "Not yet certified" >}} In service from before the [Certification](/docs/policies/lifecycle-management/certification/) policy |

### Revisions

None yet.
