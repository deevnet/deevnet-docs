---
title: "Builder & Core Services"
weight: 1
tasks_completed: 30
tasks_in_progress: 0
tasks_planned: 0
---

# Builder & Core Services ✅

Builder infrastructure, network automation, and core services required to provision and rebuild the dvntm (mobile) site from bare metal.

- **GitHub:** https://github.com/deevnet
- **Documentation:** https://deevnet.github.io/deevnet-docs/

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Achieve fully automated, repeatable provisioning of the dvntm (mobile) site from bare metal to running core services, with complete air-gap recovery capability.

**In Scope**
- Bare-metal provisioning (PXE, Ansible)
- Network infrastructure automation (switching, wireless, routing)
- Image factory for all platforms
- Full air-gap rebuild capability

**Out of Scope**
- Extended management plane (logging, telemetry, secrets, identity — separate project)
- Patch automation and firmware upgrades — see [Patch Automation](../patch-automation/)
- Full site rebuild event — see [Full Site Rebuild](../full-rebuild/)
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

{{% details "Network Automation — Complete" %}}
## Network Automation ✅

Automated configuration of network infrastructure. Migration from flat 192.168.10.0/24 to segmented 10.20.x.0/24 VLANs completed 2026-03-25. Authority transition automation completed 2026-03-26.

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
- ✅ Document automation shortcomings and improvement backlog (see migration runbook and Patch Automation project)
- ✅ Authority transition automation (bootstrap-auth/core-auth playbooks, DNS/DHCP host records from inventory, IP swap)
- ✅ Unify build sequence documentation (authority transitions and network segmentation inline)
{{% /details %}}
