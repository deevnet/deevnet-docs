---
title: "DVNTM Infrastructure Automation"
weight: 1
tasks_completed: 17
tasks_in_progress: 0
tasks_planned: 9
---

# DVNTM Infrastructure Automation

Full automation of mobile substrate provisioning and management using Infrastructure as Code (IaC) and Configuration as Code (CaC) solutions.

- **GitHub:** https://github.com/deevnet
- **Documentation:** https://deevnet.github.io/deevnet-docs/

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Achieve fully automated, repeatable provisioning of the dvntm (mobile) substrate from bare metal to running services, with complete air-gap recovery capability.

**In Scope**
- Bare-metal provisioning (PXE, Ansible)
- Network infrastructure automation
- Image factory for all platforms
- Full air-gap rebuild capability

**Out of Scope**
- Application/tenant workload automation (separate per-tenant)
- Cloud infrastructure (this is on-prem only)

---

{{% details "Requirements — Complete" %}}
## Requirements ✅

- ✅ Define substrate inventory and MAC addresses
- ✅ Define network topology and VLANs
- ✅ Define air-gap artifact requirements
{{% /details %}}

---

{{% details "Substrate Provisioning — Complete" %}}
## Substrate Provisioning ✅

Core infrastructure for building and deploying the substrate.

- ✅ Builder Node Ansible Collection (`deevnet.builder`)
- ✅ Image Packaging - Proxmox Fedora template
- ✅ Image Packaging - Proxmox installer
- ✅ Image Packaging - Raspberry Pi Base Image
- ✅ Bootstrap Node Provisioning Playbook
- ✅ Proxmox Automated Install via PXE
- ✅ Full Air-Gap Support (Fedora Mirror)
{{% /details %}}

---

{{% details "Inventory & Standards — Complete" %}}
## Inventory & Standards ✅

Documentation and inventory definitions.

- ✅ Hugo-based Documentation Site
- ✅ Standards and Correctness Docs
- ✅ dvntm Substrate Bare-Metal Inventory (MAC addresses)
{{% /details %}}

---

## Network Automation 🔄

Automated configuration of network infrastructure.

- ✅ Ansible Network Collection - DHCP reservations
- ✅ Ansible Network Collection - DNS host overrides
- ✅ OPNsense Alternatives Evaluation
- ✅ dvntm VLAN Plan
- ⏳ Access Switch Automation (Omada)
- ⏳ Proxmox Tenant Networking Design and Automation
- ⏳ Wireless AP Automation (Omada)
- ⏳ Migrate core router automation to OPNsense alternative
- ⏳ Document network build/rebuild steps in recovery plan

---

## Build Logging ⏳

Centralized logging during substrate provisioning.

- ⏳ Centralized build logging (aggregate logs from all phases)

---

## Full Substrate Rebuild Event ⏳

End-to-end rebuild of the mobile substrate from scratch. Validates full air-gap recovery capability. Completing this milestone signals the project is done.

- ⏳ Execute full substrate rebuild
- ⏳ Iterate on code and documentation fixes
- ⏳ Roadmap non-critical improvements for future work
