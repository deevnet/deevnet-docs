---
title: "DVNTM Infrastructure as Code"
weight: 1
tasks_completed: 12
tasks_in_progress: 2
tasks_planned: 15
---

# DVNTM Infrastructure as Code

Full automation of mobile substrate provisioning and management.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Substrate Provisioning ✅

Core infrastructure for building and deploying the substrate.

- ✅ Builder Node Ansible Collection (`deevnet.builder`)
- ✅ Image Packaging - Proxmox Fedora template
- ✅ Image Packaging - Proxmox installer
- ✅ Image Packaging - Raspberry Pi Base Image
- ✅ Bootstrap Node Provisioning Playbook
- ✅ Proxmox Automated Install via PXE
- ✅ Full Air-Gap Support (Fedora Mirror)

---

## Inventory & Standards ✅

Documentation and inventory definitions.

- ✅ Hugo-based Documentation Site
- ✅ Standards and Correctness Docs
- ✅ dvntm Substrate Bare-Metal Inventory (MAC addresses)

---

## Network Automation 🔄

Automated configuration of network infrastructure.

- ✅ Ansible Network Collection - DHCP reservations
- ✅ Ansible Network Collection - DNS host overrides
- 🔄 OPNsense Alternatives Evaluation
- 🔄 dvntm VLAN Plan
- ⏳ Access Switch Automation (Omada)
- ⏳ Proxmox Tenant Networking Design and Automation
- ⏳ Wireless AP Automation (Omada)

---

## Full Substrate Rebuild Event ⏳

End-to-end rebuild of the mobile substrate from scratch. Validates full air-gap recovery capability.

- ⏳ Rebuild provisioner node
- ⏳ Fetch artifacts (ISOs, install trees, containers)
- ⏳ Enable bootstrap-authoritative mode
- ⏳ Set up VLANs on access switch
- ⏳ Rebuild core router
- ⏳ Configure wireless AP
- ⏳ Rebuild Proxmox hypervisor
- ⏳ Rebuild all application tenants

---

## Day 2 Operations ⏳

Ongoing maintenance and updates.

- ⏳ Patching Strategy - Switches
- ⏳ Patching Strategy - Proxmox VE
- ⏳ Patching Strategy - Firewall/Core router
- ⏳ Patching Strategy - Linux packages
