---
title: "🛠️ Implementation & Tooling"
weight: 3
bookCollapseSection: true
---

# Implementation & Tooling

Documents **hardware and software selections** — what Deevnet runs today, and what is under
evaluation — organized by substrate architecture layer. Each page records what was chosen and why.

How to *operate* what is selected here is in the [runbook](/docs/runbook/); finished projects built
on it are under [Completed Projects](/docs/completed/).

---

## Substrate Architecture

Platform documentation follows the three-layer substrate architecture:

### Network

The **network layer** provides connectivity, routing, and network services:

- **Edge Router** — Upstream connectivity (ISP/travel router)
- **Core Router** — Internal routing, firewall, DNS, DHCP, gateway
- **Access Switch** — Layer 2 connectivity, VLAN tagging
- **Access Point** — Wireless connectivity

### Management Plane

The **management plane** provides infrastructure services for substrate management:

- **Bootstrap Node** — Ansible controller, artifact server, PXE boot
- **Management Hypervisor** — Observability, automation, access services (Proxmox Node 1)

### Tenant Compute

The **tenant compute layer** provides resources for application workloads:

- **Tenant Hypervisors** — VM-based tenant workloads (Proxmox Node 2)
- **Raspberry Pi** — Pi 4 bank for edge/IoT and hardware projects

---

## Scope

This section answers the question:
> "Why did we choose this, and under what conditions would we change it?"

Each platform page documents:

| Section | Content |
|---------|---------|
| **Purpose** | Role in the substrate |
| **Hardware** | mobile vs home hardware selections |
| **Operating System** | OS choice and automation capability |
| **Roles** | Services or functions provided |

---

## Certification

What each selection was tested against, by item: its current verdict, and every evaluation behind it,
for hardware and software. See [Certification](certification/). The process and criteria are the
[Certification](/docs/policies/certification/) policy.

---

## Software Catalog

Every piece of software in use, with its version, license and support model, grouped by layer, including
the services bundled inside OPNsense: see [Software Catalog](software-catalog/).

---

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Ansible | Infrastructure provisioning |
| Terraform | Tenant interface — tenants declare themselves through the `deevnet/deevnet` provider |
| Packer | OS image builds |
| Fedora/RHEL | Primary OS (dnf-based, SELinux) |
| Proxmox VE | Virtualization platform |
| OPNsense | Router platform |
| VyOS | Under evaluation (see [Evaluations](/docs/platforms/evaluations/)) |
| TP-Link Omada | Switch and AP management |
