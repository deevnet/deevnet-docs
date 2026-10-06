---
title: "Builder Node"
weight: 1
bookCollapseSection: true
aliases:
  - /docs/platforms/management-plane/bootstrap-node/
---

# Builder Node

Fills the **builder** role — see [Builder](/docs/architecture/builder/). The host is `dv00bld001p01`.

---

## Hardware

[AOOSTAR N1 PRO](/docs/platforms/hardware/compute/aoostar-n1-pro/): specs, cabling, power and console.

---

## Operating System

The Builder runs Fedora Workstation, configured via the `deevnet.builder` Ansible collection.

| Attribute | Value |
|-----------|-------|
| **OS** | Fedora Workstation |
| **Version** | [Software Catalog](/docs/platforms/software-catalog/#builder-dv00bld001p01-and-the-provisioner-vms) |
| **Collection** | `deevnet.builder` applied |

The Builder is installed over PXE by another builder: a temporary builder VM on the management hypervisor network-boots it with the builder kickstart, then applies the full builder configuration. See [Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/).

---

## Network Position

The dual-homed position is described in [Builder → Network Position](/docs/architecture/builder/#network-position).
On this host, from inventory:

| Interface | Purpose | Address |
|-----------|---------|---------|
| `eth0` | Management segment (downstream) | `10.20.99.95` reserved; `10.20.99.1` while bootstrap-authoritative |
| `eth1` | Transit | DHCP |
| `wifi` | Upstream (WAN) | from whatever network it joins |

---

## Roles

The Builder is configured using these `deevnet.builder` roles:

| Role | Purpose |
|------|---------|
| **[Workstation](workstation-role/)** | Developer tools, users, Ansible controller |
| **[Artifacts](artifacts-role/)** | Air-gapped artifact serving (ISOs, packages, images) |
| **[Bootstrap](bootstrap-role/)** | Network boot for the site: PXE and TFTP always; DNS, DHCP and gateway too while the Builder is authoritative |
| **[Network Controller](network-controller-role/)** | A stopped, empty Omada controller and a copy of the live controller's snapshot: the cold fallback for `dv02nms001v01` |

---

## Service Identity

Per the [Naming Standard](/docs/standards/naming/):

- `dv00bld001p01.mobile.deevnet.net` — the host itself
- `artifacts.mobile.deevnet.net` → `dv00bld001p01.mobile.deevnet.net` (CNAME)
- `pxe.mobile.deevnet.net` → `dv00bld001p01.mobile.deevnet.net` (CNAME)

Per [Multihoming](/docs/standards/correctness/#33-multihoming-service-co-location), the Builder hosts multiple services. This co-location is intentional and documented—blast radius is understood.
