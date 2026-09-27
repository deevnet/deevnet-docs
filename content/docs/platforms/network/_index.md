---
title: "Network"
weight: 2
bookCollapseSection: true
---

# Network

The products that fill the network roles. What each role does, and where it sits, is in
[Substrate Networking](/docs/architecture/substrate/networking/).

| Role | Product | Page |
|------|---------|------|
| Edge router | GL-iNet Slate AX, OpenWrt | [Edge Router](edge-router/) |
| Core router | ZimaBoard 832, OPNsense | [Core Router](core-router/) |
| Access switch | TP-Link SG2218 | [Access Switch](access-switch/) |
| Wireless access | TP-Link EAP650-Outdoor | [Wireless Access Point](access-point/) |
| Network management | Omada SDN Controller | [Network Controllers](network-controllers/) |

---

## Automation

Network infrastructure is configured via Ansible, from the `deevnet.net` collection:

| Device | Interface | Notes |
|--------|-----------|-------|
| Core Router | OPNsense REST API | One role per service: VLAN interfaces, firewall rules and aliases (pf), DNS (Unbound), DHCP (Kea), gateways and routes. Interface IP configuration has no API (as of 25.7). The bundled services in use are in the [Software Catalog](/docs/platforms/software-catalog/#core-router-opnsense-dv02cor002p01) |
| Access Switch | SSH CLI (`switch_vlans`) | Standalone. Adoption into the Omada controller is [CHG-0009](/docs/changes/2026/0009-access-switch-adoption/), on hold |
| Wireless Access Point | Omada controller Open API | Adopted; the controller provisions the SSIDs and PPSK keys from inventory |
| Edge Router | None | Not managed by automation |

To run it, see [Build Network: Applying Configuration](/docs/runbook/substrate/building-recovery/build-network/#applying-configuration).
