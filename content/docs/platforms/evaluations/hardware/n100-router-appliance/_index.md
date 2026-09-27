---
title: "N100 Router Appliance"
weight: 1
bookCollapseSection: true
---

# N100 Router Appliance

| | |
|---|---|
| **Role** | Core router, replacing the [ZimaBoard 832](/docs/platforms/hardware/network/zimaboard-832/) |
| **Current** | {{< status-badge "planned" "Not yet evaluated" >}} Requirements set; no model chosen yet |

A future hardware evaluation. The current core router (ZimaBoard 832) is a general-purpose SBC repurposed as a router. Purpose-built Intel N100 router appliances offer better performance, more Ethernet ports, and a form factor designed for the role.

## Why N100 Router Appliances?

| Attribute | Current (ZimaBoard 832) | N100 Appliance |
|-----------|--------------------------|----------------|
| **CPU** | Celeron N3450 | Intel N100 (4C, 3.4GHz boost) |
| **Ethernet** | 2x 1GbE | 4x 2.5GbE (typical) |
| **TDP** | 6-12W | 6W |
| **Cooling** | Passive | Fanless (typical) |
| **NVMe** | None built in (PCIe x4 expansion only) | Built-in M.2 slot |
| **Form factor** | SBC (not router-specific) | Mini PC / firewall appliance |
| **Purpose** | General-purpose | Built for routing/firewall |

## Provisioning Model Change

This evaluation also introduces a future shift in the provisioning approach for the core router:

| Aspect | Current Model | Future Model |
|--------|---------------|--------------|
| **Install method** | Manual USB install | Pre-imaged NVMe drive |
| **Storage** | eMMC (soldered) | Removable NVMe M.2 |
| **Recovery** | Reinstall from USB | Swap in pre-imaged NVMe |
| **Imaging** | Manual | Scripted image-to-NVMe (on build host) |

**Pre-imaged NVMe** means the OPNsense installation is written to an NVMe drive on a build host, then physically installed in the router appliance. This approach:

- Eliminates the need for PXE or USB boot during provisioning
- Enables offline preparation of recovery drives
- Aligns with air-gap recovery requirements (spare NVMe kept ready)
- Fits the image factory model already used for other substrate hosts

This provisioning model is part of the N100 evaluation, not the current MVP approach.

## Role Requirements

What the core router role needs from a candidate, beyond the
[hardware criteria](/docs/policies/lifecycle-management/evaluation/hardware-evaluation/#criteria)
every model is checked against. These are H10 (role minimums) for this role.

| Requirement | Minimum | Why |
|-------------|---------|-----|
| **CPU** | Intel N100 or equivalent | |
| **Ethernet** | 4x 2.5GbE, Intel NICs preferred over Realtek | [INC-0004](/docs/incidents/2026/0004-core-router-lost/): a Realtek NIC timing out in service. H4 is the test |
| **NVMe** | M.2 slot for removable NVMe storage | Pre-imaged recovery disks (H1, H3) |
| **Cooling** | Fanless preferred | H8 |
| **RAM** | 8GB | |
| **OPNsense compatibility** | FreeBSD driver support for its NICs | H4 is run on OPNsense, not another OS |

## Status

| Phase | Status |
|-------|--------|
| Requirements definition | Complete |
| Hardware research | Pending |
| OPNsense NVMe imaging workflow | Pending |
| Procurement | Pending |
| Validation | Pending |

## Revisions

None yet. The first revision opens when a model is chosen for the bench.
