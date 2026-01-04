---
title: "DVNTM Infrastructure as Code"
weight: 1
---

# DVNTM Infrastructure as Code

Full automation of mobile substrate provisioning and management.

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Milestone: Substrate Provisioning ✅

Core infrastructure for building and deploying the substrate.

| Task | Status |
|------|--------|
| Builder Collection (`deevnet.builder`) | ✅ |
| Image Packaging - Proxmox Fedora template | ✅ |
| Image Packaging - Proxmox installer | ✅ |
| Raspberry Pi Base Image | ✅ |
| Bootstrap Node Provisioning Playbook | ✅ |
| Proxmox Automated Install via PXE | ✅ |
| Full Air-Gap Support | ✅ |

---

## Milestone: Inventory & Standards ✅

Documentation and inventory definitions.

| Task | Status |
|------|--------|
| Standards and Correctness Docs | ✅ |
| dvntm Substrate Inventory (MAC addresses) | ✅ |

---

## Milestone: Network Automation ⏳

Automated configuration of network infrastructure.

| Task | Status |
|------|--------|
| Ansible Network Collection - DHCP reservations | ✅ |
| Ansible Network Collection - DNS host overrides | ✅ |
| OPNsense Alternatives Evaluation | ⏳ |
| dvntm VLAN Plan | ⏳ |
| Access Switch Automation (Omada) | ⏳ |
| Proxmox Tenant Networking | ⏳ |
| Wireless AP Automation (Omada) | ⏳ |

---

## Milestone: Full Substrate Rebuild ⏳

End-to-end rebuild of the mobile substrate from scratch.

| Step | Task | Status |
|------|------|--------|
| 1 | Rebuild provisioner node | ⏳ |
| 2 | Fetch artifacts (ISOs, install trees, containers) | ⏳ |
| 3 | Enable bootstrap-authoritative mode | ⏳ |
| 4 | Set up VLANs | ⏳ |
| 5 | Rebuild core router | ⏳ |
| 6 | Configure wireless AP | ⏳ |
| 7 | Rebuild Proxmox hypervisor | ⏳ |
| 8 | Rebuild all application tenants | ⏳ |

Validates full air-gap recovery capability.

---

## Milestone: Day 2 Operations ⏳

Ongoing maintenance and updates.

| Task | Status |
|------|--------|
| Patching Strategy - Proxmox VE | ⏳ |
| Patching Strategy - Firewall/router | ⏳ |
| Patching Strategy - Linux packages | ⏳ |
