---
title: "🛠️ Implementation & Tooling"
weight: 4
bookCollapseSection: true
---

# Implementation & Tooling

Documents **what each role runs and how it is configured** — what Deevnet runs today, and what is
under evaluation — organized by substrate architecture layer. Each page records what was chosen and
why. The section opens with [Hardware](hardware/): the physical boxes, one page per model.

How to *operate* what is selected here is in the [runbook](/docs/runbook/); finished projects built
on it are under [Completed Projects](/docs/completed/).

---

## Roles and what fills them

The roles themselves — what each does, and where it sits in the network — are defined in
[Architecture](/docs/architecture/). This section only says what fills them.

| Architecture role | Filled by | Page |
|---|---|---|
| [Edge router](/docs/architecture/substrate/networking/#edge-router-role) | GL-iNet Slate AX, OpenWrt | [Edge Router](network/edge-router/) |
| [Core router](/docs/architecture/substrate/networking/#core-router-role) | ZimaBoard 832, OPNsense | [Core Router](network/core-router/) |
| [Access switch](/docs/architecture/substrate/networking/#switching) | TP-Link SG2218 | [Access Switch](network/access-switch/) |
| [Wireless access](/docs/architecture/substrate/networking/#wireless) | TP-Link EAP650-Outdoor | [Wireless Access Point](network/access-point/) |
| [Network management](/docs/architecture/substrate/management-plane/#network-management) | Omada SDN Controller | [Network Controllers](network/network-controllers/) |
| [Builder](/docs/architecture/builder/) | AOOSTAR N1 PRO, Fedora | [Bootstrap Node](management-plane/bootstrap-node/) |
| [Management hypervisor](/docs/architecture/substrate/compute/#compute-by-purpose) | Dell OptiPlex 7050 Micro, Proxmox VE | [Management Hypervisor](management-plane/management-hypervisor/) |
| [Tenant hypervisor](/docs/architecture/substrate/compute/#compute-by-purpose) | Dell OptiPlex 7060 Micro, Proxmox VE | [Tenant Hypervisors](tenant-compute/tenant-hypervisors/) |
| [Tenant fabric](/docs/architecture/tenant/networking/) | Proxmox SDN, EVPN/VXLAN | [Tenant Fabric](tenant-compute/tenant-hypervisors/tenant-fabric/) |
| [Pi lab](/docs/architecture/substrate/compute/#the-pi-lab) | Raspberry Pi 4 | [Raspberry Pi](tenant-compute/raspberry-pi/) |
| [Tenant DNS](/docs/architecture/substrate/control-plane/#identity) | PowerDNS Authoritative | [Tenant DNS](management-plane/tenant-dns/) |

The software this site wrote for itself — the Deevnet API, the Terraform provider tenants use, and
the runtime tools around them — is [Deevnet Software](deevnet-software/). Everything else the
management and control planes run — OpenBao, the MQTT broker, the log store, Grafana — is listed in
the [Software Catalog](software-catalog/).

---

## Scope

This section answers the question:
> "Why did we choose this, and under what conditions would we change it?"

Each role page documents:

| Section | Content |
|---------|---------|
| **Role** | One line naming the architecture role it fills, with a link |
| **Hardware** | A link to the model's page under [Hardware](/docs/platforms/hardware/) |
| **Operating System** | OS choice and automation capability |
| **Product features in use** | What the product does beyond the role, and the product-specific facts that cost time to discover |

It does not restate the role, and it holds no procedures: those are in the [runbook](/docs/runbook/).

---

## Evaluations

What each selection was checked against, by item: its current verdict, and every evaluation behind
it, plus the candidates being considered. See [Evaluations](evaluations/). Hardware in service is
evaluated on its model's [Hardware](/docs/platforms/hardware/) page. The process and criteria are the
[Evaluation](/docs/policies/lifecycle-management/evaluation/) policy.

---

## Software Catalog

Every piece of software in use, with its version, license and support model, grouped by layer, including
the services bundled inside OPNsense: see [Software Catalog](software-catalog/).

---

## Technology Stack

| Technology | Purpose |
|------------|---------|
| Ansible | Infrastructure provisioning |
| Terraform | Tenant interface — tenants declare themselves through the `deevnet/deevnet` provider |
| Packer | OS image builds |
| Fedora/RHEL | Primary OS (dnf-based, SELinux) |
| Proxmox VE | Virtualization platform |
| OPNsense | Router platform |
| VyOS | On hold (see [Evaluations](/docs/platforms/evaluations/)) |
| TP-Link Omada | Switch and AP management |
