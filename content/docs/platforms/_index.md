---
title: "Platforms & Tooling"
weight: 3
bookCollapseSection: true
---

# Platforms & Tooling

Documents **hardware and software platform decisions**, including rationale and trade-offs.

## Scope

This section includes:
- Operating system choices (e.g., why Fedora)
- Network platforms (e.g., why OPNsense)
- Virtualization platforms (e.g., why Proxmox)
- Toolchain selections (Ansible, Terraform, Packer, etc.)
- Criteria for adopting or rejecting technologies

This section answers the question:
> "Why did we choose this, and under what conditions would we change it?"

---

## Infrastructure Components

Detailed documentation for substrate infrastructure:

- [Bootstrap Node](bootstrap-node/) — Control plane for substrate provisioning
- [OPNsense Router](opnsense-router/) — Current firewall, gateway, DNS, DHCP
- [VyOS Router](vyos-router/) — Target router platform (evaluation)
- [Proxmox Hypervisors](proxmox-hypervisors/) — Virtualization platform
