---
title: "DVNTM Infrastructure as Code"
weight: 1
---

# DVNTM Infrastructure as Code

Full automation of mobile substrate provisioning and management.

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

Each section below represents a project milestone.

---

## Substrate Provisioning ✅

Core infrastructure for building and deploying the substrate.

| Task | Status |
|------|--------|
| Builder Node Ansible Collection (`deevnet.builder`) | ✅ |
| Image Packaging - Proxmox Fedora template | ✅ |
| Image Packaging - Proxmox installer | ✅ |
| Image Packaging - Raspberry Pi Base Image | ✅ |
| Bootstrap Node Provisioning Playbook | ✅ |
| Proxmox Automated Install via PXE | ✅ |
| Full Air-Gap Support (Fedora Mirror) | ✅ |

---

## Inventory & Standards ✅

Documentation and inventory definitions.

| Task | Status |
|------|--------|
| Hugo-based Documentation Site | ✅ |
| Standards and Correctness Docs | ✅ |
| dvntm Substrate Bare-Metal Inventory (MAC addresses) | ✅ |

---

## Network Automation ⏳

Automated configuration of network infrastructure.

| Task | Status |
|------|--------|
| Ansible Network Collection - DHCP reservations | ✅ |
| Ansible Network Collection - DNS host overrides | ✅ |
| OPNsense Alternatives Evaluation | ⏳ |
| dvntm VLAN Plan | ⏳ |
| Access Switch Automation (Omada) | ⏳ |
| Proxmox Tenant Networking Design and Automation | ⏳ |
| Wireless AP Automation (Omada) | ⏳ |

---

## Full Substrate Rebuild Event ⏳

End-to-end rebuild of the mobile substrate from scratch.

| Step | Task | Status |
|------|------|--------|
| 1 | Rebuild provisioner node | ⏳ |
| 2 | Fetch artifacts (ISOs, install trees, containers) | ⏳ |
| 3 | Enable bootstrap-authoritative mode | ⏳ |
| 4 | Set up VLANs on access switch | ⏳ |
| 5 | Rebuild core router | ⏳ |
| 6 | Configure wireless AP | ⏳ |
| 7 | Rebuild Proxmox hypervisor | ⏳ |
| 8 | Rebuild all application tenants | ⏳ |

Validates full air-gap recovery capability.

---

## Day 2 Operations ⏳

Ongoing maintenance and updates.

| Task | Status |
|------|--------|
| Patching Strategy - Switches | ⏳ |
| Patching Strategy - Proxmox VE | ⏳ |
| Patching Strategy - Firewall/Core router | ⏳ |
| Patching Strategy - Linux packages | ⏳ |
