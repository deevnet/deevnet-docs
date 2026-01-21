---
title: "Platforms & Tooling"
weight: 3
bookCollapseSection: true
---

# Platforms & Tooling

Documents **hardware and software platform decisions**, organized by substrate architecture layer.

---

## Substrate Architecture

Platform documentation follows the three-layer substrate architecture:

### Network

The **network layer** provides connectivity, routing, and network services:

- **Edge Router** — Upstream connectivity (ISP/travel router)
- **Core Router** — Internal routing, firewall, DNS, DHCP, gateway
- **Access Switch** — Layer 2 connectivity, VLAN tagging
- **Access Point** — Wireless connectivity

### Control Plane

The **control plane** provides infrastructure services for substrate management:

- **Bootstrap Node** — Ansible controller, artifact server, PXE boot
- **Management Hypervisor** — Observability, automation, access services (Proxmox Node 1)

### Tenant Compute

The **tenant compute layer** provides resources for application workloads:

- **Tenant Hypervisors** — VM-based tenant workloads (Proxmox Node 2)
- **Raspberry PIs** — Edge/IoT compute

---

## Scope

This section answers the question:
> "Why did we choose this, and under what conditions would we change it?"

Each platform page documents:

| Section | Content |
|---------|---------|
| **Purpose** | Role in the substrate |
| **Hardware** | dvntm vs dvnt hardware selections |
| **Operating System** | OS choice and automation capability |
| **Roles** | Services or functions provided |

---

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Ansible | Infrastructure provisioning |
| Terraform | Tenant VM lifecycle (future) |
| Packer | OS image builds |
| Fedora/RHEL | Primary OS (dnf-based, SELinux) |
| Proxmox VE | Virtualization platform |
| OPNsense | Router platform |
| VyOS | Under evaluation (see [Evaluations](/docs/platforms/evaluations/)) |
| TP-Link Omada | Switch and AP management |
