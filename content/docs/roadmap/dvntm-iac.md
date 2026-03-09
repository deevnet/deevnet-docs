---
title: "DVNTM Builder & Core Services"
weight: 1
tasks_completed: 19
tasks_in_progress: 2
tasks_planned: 8
---

# DVNTM Builder & Core Services

Builder infrastructure, network automation, and core services required to provision and rebuild the dvntm (mobile) site from bare metal.

- **GitHub:** https://github.com/deevnet
- **Documentation:** https://deevnet.github.io/deevnet-docs/

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Achieve fully automated, repeatable provisioning of the dvntm (mobile) site from bare metal to running core services, with complete air-gap recovery capability. Culminates in a full site rebuild event.

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
- ✅ dvntm Site Bare-Metal Inventory (MAC addresses)
{{% /details %}}

---

## Network Automation 🔄

Automated configuration of network infrastructure.

- ✅ OPNsense Alternatives Evaluation
- 🔄 Document network build/rebuild steps in recovery plan
- ✅ dvntm VLAN Plan
- ✅ DNS Automation
- ✅ DHCP Automation
- 🔄 Core Router Automation
- ⏳ Access Switch Automation
- ⏳ Wireless AP Automation

---

## Full Site Rebuild Event ⏳

End-to-end rebuild of the builder node and core network services from scratch. Validates air-gap recovery capability and exercises all automation built in prior milestones. Completing this milestone signals the builder & core services project is done.

- ⏳ Read and analyze the build/recovery plan
- ⏳ Rebuild the builder node (no version bump)
- ⏳ Rebuild core services (core router, access switch, AP) — collect timings, findings, and identify gaps
- ⏳ Apply fixes and iterate until all steps are accounted for
- ⏳ Roadmap non-critical improvements for future work
- ⏳ Tag all deevnet repos with a coordinated release version
