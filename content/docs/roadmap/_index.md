---
title: "Roadmap"
weight: 5
bookCollapseSection: true
---

# Roadmap

Captures **forward-looking intent** that is shared across projects.

Roadmaps are **informational**, not binding contracts.

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Milestones

### 1. ✅ Builder Collection
`deevnet.builder`

Ansible collection for provisioning, artifacts, and PXE bootstrap.

---

### 2. ✅ Image Packaging
`deevnet-image-factory`

Packer-based image builds:
- ✅ Proxmox Fedora template
- ✅ Proxmox installer (see item 7)
- ✅ Raspberry Pi images (see item 8)

---

### 3. ✅ Standards and Correctness Docs
`deevnet-docs`

Correctness, naming, and architecture documentation.

---

### 4. ✅ Ansible Network Collection
`deevnet.net`

Inventory-driven OPNsense network configuration:
- DHCP static reservations via Kea API
- DNS host overrides and aliases via Unbound API

---

### 5. ✅ dvntm Substrate Inventory

Bare metal hardware inventory with MAC addresses for network provisioning:

| Qty | Device |
|-----|--------|
| 1x | Travel router (upstream gateway) |
| 1x | 24-port Omada switch |
| 1x | OPNsense firewall/router |
| 1x | Proxmox server |
| 1x | TP-Link wireless AP |
| 4x | Raspberry Pi |

---

### 6. ✅ Bootstrap Node Provisioning Playbook

Playbook to configure PXE, DHCP, and DNS on the bootstrap node.

Enables bootstrap-authoritative mode for substrate provisioning.

---

### 7. ✅ Proxmox Automated Install

Automated Proxmox installation via PXE.

Part of `deevnet-image-factory`.

---

### 8. ✅ Raspberry Pi Image Generation

Packer-based Pi image builds.

Part of `deevnet-image-factory`.

**Subtask:** Software Defined Radio (SDR) image.

---

### 9. ✅ Full Air-Gap Support

Complete air-gapped provisioning for substrate layer:

- ✅ Fedora install tree mirror
- ✅ Fedora/Proxmox ISOs on artifact server
- ✅ Proxmox VM template (kickstart uses cdrom)
- ✅ Proxmox VE bare metal (embedded answer files)

**Excludes:** Raspberry Pi (different OS, out of scope for substrate air-gap).

See [Operational Runbook - Building & Recovery](/docs/runbook/building-recovery/) for procedures.

---

### 10. ⏳ OPNsense Alternatives Evaluation

Evaluate firewall/router alternatives that support automated PXE installation.

Current OPNsense lacks PXE install support, limiting full air-gap automation.

---

### 11. ⏳ dvntm VLAN Plan

Define VLAN topology for mobile substrate:

- Tenant VLAN assignments
- IP ranges per VLAN
- Inter-VLAN routing rules
- Guest network isolation

---

### 12. ⏳ Access Switch Automation

Automate Omada switch configuration via `deevnet.net` collection:

- VLAN creation and port assignments
- Trunk/access port configuration
- LACP/port channel setup

---

### 13. ⏳ Proxmox Tenant Networking

Each tenant isolated in its own network segment.

Tasks:
- Pre-allocate VLAN IDs per tenant (e.g., VLAN 100=grooveiq, 101=vintronics, 102=iot-backend)
- Configure Proxmox bridges with VLAN tagging support
- Define IP ranges per tenant VLAN
- Firewall rules for inter-tenant isolation / routing
- Integrate tenant VLAN definitions into inventory (config-as-code)

---

### 14. ⏳ Wireless AP Automation

Automate TP-Link Omada AP configuration via `deevnet.net` collection:

- SSID provisioning
- Guest network isolation
- VLAN assignments per SSID

---

### 15. ⏳ dvntm Substrate Rebuild

End-to-end rebuild of the mobile substrate from scratch:

1. Rebuild provisioner node
2. Fetch artifacts (ISOs, install trees, containers)
3. Enable bootstrap-authoritative mode
4. Set up VLANs
5. Rebuild core router
6. Configure wireless AP
7. Rebuild Proxmox hypervisor
8. Rebuild all application tenants

Validates full air-gap recovery capability.

---

### 16. ⏳ Patching Strategy

Define approach for keeping infrastructure components up to date:

- Proxmox VE hypervisors
- Firewall/router (OPNsense or alternative)
- Linux packages on provisioned hosts
