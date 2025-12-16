---
title: "Roadmap"
weight: 3
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

### 2. 🔄 Image Packaging
`deevnet-image-factory`

Packer-based image builds:
- ✅ Proxmox Fedora template
- ⏳ Proxmox installer (see item 7)
- ⏳ Raspberry Pi images (see item 8)

---

### 3. ✅ Standards and Correctness Docs
`deevnet-docs`

Correctness, naming, and architecture documentation.

---

### 4. 🔄 Ansible Network Collection
`deevnet.net`

OPNsense and Omada configuration automation.

---

### 5. ⏳ dvntm Substrate Inventory

Bare metal hardware inventory with MAC addresses for network provisioning:

| Qty | Device |
|-----|--------|
| 1x | Travel router (upstream gateway) |
| 1x | 24-port Omada switch |
| 1x | OPNsense firewall/router |
| 2x | Proxmox hypervisors |
| 1x | TP-Link wireless AP |
| 4x | Raspberry Pi |

---

### 6. ⏳ Bootstrap Node Provisioning Playbook

Playbook to configure PXE, DHCP, and DNS on the bootstrap node.

Enables bootstrap-authoritative mode for substrate provisioning.

---

### 7. ⏳ Proxmox Automated Install

Automated Proxmox installation via PXE.

Part of `deevnet-image-factory`.

---

### 8. ⏳ Raspberry Pi Image Generation

Packer-based Pi image builds.

Part of `deevnet-image-factory`.

**Subtask:** Software Defined Radio (SDR) image.

---

### 9. ⏳ Proxmox Tenant Networking

Each tenant isolated in its own network segment.

Tasks:
- Pre-allocate VLAN IDs per tenant (e.g., VLAN 100=grooveiq, 101=vintronics, 102=iot-backend)
- Configure Proxmox bridges with VLAN tagging support
- Define IP ranges per tenant VLAN
- OPNsense rules for inter-tenant isolation / routing
- Integrate tenant VLAN definitions into inventory (config-as-code)

---

### 10. ⏳ Full Air-Gap Support

Complete air-gapped provisioning for substrate layer:
- OPNsense
- Proxmox
- Builder/Bootstrap node

**Excludes:** Raspberry Pi (different OS, out of scope for substrate air-gap).

Requires local package mirrors (dnf reposync).
