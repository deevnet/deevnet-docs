---
title: "DVNTM Builder & Core Services"
weight: 1
tasks_completed: 28
tasks_in_progress: 0
tasks_planned: 13
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

## Network Automation ✅

Automated configuration of network infrastructure. Migration from flat 192.168.10.0/24 to segmented 10.20.x.0/24 VLANs completed 2026-03-25.

- ✅ OPNsense Alternatives Evaluation
- ✅ Document network build/rebuild steps in recovery plan
- ✅ dvntm VLAN Plan
- ✅ DNS Automation
- ✅ DHCP Automation (Kea subnets auto-created, interface enablement automated)
- ✅ Core Router Automation (OPNsense VLAN creation, firewall rules via API)
- ✅ Access Switch Automation (SG2218 General mode, VLANs, trunk, access ports, default gateway)
- ✅ Implement Network Segmentation (12 VLANs, zone-based firewall policy)
- ✅ Migrate to RFC1918 10 space (10.20.x.0/24 subnets live)
- ✅ Wireless AP SSID-to-VLAN configuration (manual via standalone UI — automation gap documented)
- ✅ Document automation shortcomings and improvement backlog (see migration runbook To Do section and DVNTM Patch Automation below)

---

## DVNTM Patch Automation ⏳

Firmware upgrades and automation improvements identified during the network migration. These are non-blocking enhancements — the network is fully functional, but these items improve automation coverage, idempotency, and reduce manual steps for future rebuilds.

### Firmware Upgrades
- ⏳ EAP650-Outdoor AP firmware update (1.0.4 → latest) — current firmware doesn't accept VLAN config from Omada 6.1 controller, requiring manual standalone UI configuration
- ⏳ SG2218 Access Switch firmware update — evaluate newer firmware for improved CLI compatibility and Omada integration

### Automation Improvements
- ⏳ Automate OPNsense interface assignment and IP config via SSH (eliminate manual GUI steps — OPNsense 25.7 has no API for this)
- ⏳ TP-Link SG2218 cliconf idempotency (proper config diff support in the Ansible cliconf plugin)
- ⏳ OPNsense automation filter API investigation (addRule saves but doesn't compile to pf on 25.7.10)
- ⏳ Omada SSID VLAN provisioning via controller after AP firmware update
- ⏳ Replace curl-based Omada API tasks with Ansible uri module (eliminate command-line secret exposure)

---

## Full Site Rebuild Event ⏳

End-to-end rebuild of the builder node and core network services from scratch. Validates air-gap recovery capability and exercises all automation built in prior milestones. Completing this milestone signals the builder & core services project is done.

- ⏳ Read and analyze the build/recovery plan
- ⏳ Rebuild the builder node (no version bump)
- ⏳ Rebuild core services (core router, access switch, AP) — collect timings, findings, and identify gaps
- ⏳ Apply fixes and iterate until all steps are accounted for
- ⏳ Roadmap non-critical improvements for future work
- ⏳ Tag all deevnet repos with a coordinated release version
