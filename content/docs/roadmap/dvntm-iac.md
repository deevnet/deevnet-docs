---
title: "DVNTM Builder & Core Services"
weight: 1
tasks_completed: 19
tasks_in_progress: 2
tasks_planned: 5
---

# DVNTM Builder & Core Services

Builder infrastructure, network automation, and core services required to provision and rebuild the dvntm (mobile) substrate from bare metal.

- **GitHub:** https://github.com/deevnet
- **Documentation:** https://deevnet.github.io/deevnet-docs/

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Achieve fully automated, repeatable provisioning of the dvntm (mobile) substrate from bare metal to running core services, with complete air-gap recovery capability. Culminates in a full substrate rebuild event.

**In Scope**
- Bare-metal provisioning (PXE, Ansible)
- Network infrastructure automation (switching, wireless, routing)
- Image factory for all platforms
- Full air-gap rebuild capability

**Out of Scope**
- Extended management plane (logging, telemetry, secrets, identity — separate project)
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

- ✅ OPNsense Alternatives Evaluation
- ✅ dvntm VLAN Plan
- ✅ DNS Automation
- ✅ DHCP Automation
- 🔄 Core Router Automation
- 🔄 Document network build/rebuild steps in recovery plan
- ⏳ Access Switch Automation
- ⏳ Wireless AP Automation

---

## Full Substrate Rebuild Event ⏳

End-to-end rebuild of the mobile substrate from scratch. Validates full air-gap recovery capability. Completing this milestone signals the project is done.

- ⏳ Execute full substrate rebuild
- ⏳ Iterate on code and documentation fixes
- ⏳ Roadmap non-critical improvements for future work
