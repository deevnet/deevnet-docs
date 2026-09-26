---
title: "Network"
weight: 1
bookCollapseSection: true
---

# Network

The **network layer** provides connectivity, routing, and network services for all substrate infrastructure.

This section documents network devices that form the physical and logical foundation for substrate connectivity:

- **Edge Router** — Upstream connectivity and WAN interface
- **Core Router** — Internal routing, firewall, DNS, DHCP, and gateway services
- **Access Switch** — Layer 2 connectivity for substrate hosts
- **Access Point** — Wireless connectivity for mobile and IoT devices

---

## Network Services

Network devices collectively provide:

| Service | Provider |
|---------|----------|
| **DNS** | Core Router (authoritative for substrate zone) |
| **DHCP** | Core Router (static mappings + dynamic pool) |
| **Gateway** | Core Router (default route for substrate) |
| **Firewall** | Core Router (NAT, inter-VLAN rules) |
| **VLAN tagging** | Access Switch |
| **Wireless** | Access Point (managed by Omada controller) |

---

## Automation

Network infrastructure is configured via Ansible, from the `deevnet.net` collection:

| Device | How | Notes |
|--------|-----|-------|
| Core Router | OPNsense REST API | One role per service, run in order by `playbooks/opnsense.yml`: VLAN interfaces, firewall rules and aliases (pf), DNS (Unbound), DHCP (Kea), gateways and routes. Interface IP configuration has no API (as of 25.7), so the VLAN role pauses while it is done in the GUI. The bundled services in use are in the [Software Catalog](/docs/platforms/software-catalog/#core-router-opnsense-dv02cor002p01) |
| Access Switch | SSH CLI (`switch_vlans`) | Standalone. Adoption into the Omada controller is [CHG-0009](/docs/changes/2026/0009-access-switch-adoption/), on hold |
| Access Point | Omada controller Open API (`omada-wireless.yml`) | Adopted; the controller provisions the SSIDs and PPSK keys from inventory |
| Edge Router | None | Not managed by automation |
