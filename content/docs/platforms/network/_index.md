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

Network infrastructure is configured via Ansible:

| Device | Collection | Notes |
|--------|------------|-------|
| Core Router | `vyos.vyos` (target) | VyOS CLI-based automation |
| Core Router | `deevnet.net` (current) | OPNsense API-based automation |
| Access Switch | Omada controller | TP-Link SDN management |
| Access Point | Omada controller | TP-Link SDN management |
