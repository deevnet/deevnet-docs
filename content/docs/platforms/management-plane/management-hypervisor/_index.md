---
title: "Management Hypervisor"
weight: 2
bookCollapseSection: true
---

# Management Hypervisor

Fills the **management hypervisor** role — the host for the site's management and control plane
substrate service VMs. See [Substrate Compute → Compute by purpose](/docs/architecture/substrate/compute/#compute-by-purpose).
The host is `dv02hyp001p01`; the service VMs it carries are listed in the
[Software Catalog](/docs/platforms/software-catalog/#substrate-service-vms).

---

## Hardware

[Dell OptiPlex 7050 Micro](/docs/platforms/hardware/compute/dell-optiplex-7050-mff/): specs, cabling, power and console.

---

## Operating System

The management hypervisor runs Proxmox VE.

| Attribute | Value |
|-----------|-------|
| **OS** | Proxmox VE |
| **Version** | [Software Catalog](/docs/platforms/software-catalog/#management-hypervisor-dv02hyp001p01) |
| **Base** | Debian |

### Automation Capability

- **Installation**: manual, from the standard Proxmox VE ISO. An unattended ISO (embedded answer
  file, install disk pinned by serial) is [unfinished work](/docs/roadmap/infrastructure/mobile/builder/) in `deevnet-image-factory`
- **Post-install**: Ansible: `deevnet.builder` (`proxmox_node_base`, `proxmox_node_storage`) and
  `deevnet.net` (`proxmox_node_network`, bridge only on this node)
- **VM provisioning**: Ansible-only (no Terraform for management plane)
- **Templates**: Packer-built Fedora templates stored locally

Proxmox is treated as an API surface for management workloads, not a declarative state engine.

---

## VM Templates

| Template | Description |
|----------|-------------|
| **Fedora** | Ansible-ready base image built via deevnet-image-factory |

Templates are built using Packer and stored locally on each hypervisor. New VMs clone from templates for rapid, consistent deployment.

---

## Deterministic MAC Addressing

For management-hypervisor VMs, network identity must be stable and reproducible.

### Policy

- Proxmox does **not** generate deterministic MAC addresses automatically
- All management-hypervisor VMs explicitly define MAC addresses
- A MAC is **derived from the VM's Proxmox VMID** inside the locally
  administered `02:de:<site octet>` namespace, then written into
  version-controlled inventory
- DHCP and DNS rely on these fixed MACs

"Generated outside Proxmox" is not by itself enough — any hand-typed value
satisfies it, including one copied off a running guest that carries Proxmox's
own vendor OUI. The rule is that the value is **derived**, and the derivation is
a pure function of a declared VMID. See the
[MAC Namespace Specification](/docs/standards/mac-naming/) for the encoding and
its rationale.

Because the VMID is the sole source of the MAC, **changing a VMID is a
renumbering**: the MAC, the DHCP reservation and the address move together.

Since this node is not clustered (below), VMID uniqueness across the substrate
is not something Proxmox can enforce. It is enforced by the allocator in
[Allocate VM Identity](/docs/runbook/substrate/building-recovery/vm-identity/), which
surveys every hypervisor before issuing one.

This enables:
- Stable DHCP reservations
- Predictable IP addressing
- Safe VM rebuilds without network reconfiguration
- Clear mapping between hostnames, MACs, and VMIDs

---

## Non-Clustered Design

The node is a standalone Proxmox host, not a cluster member: no HA manager, no shared storage, and
its own web UI. Why nothing is clustered is in
[Substrate Compute → Nothing is clustered](/docs/architecture/substrate/compute/#nothing-is-clustered).

---

## Provisioning Workflow

The node is installed by hand from the Proxmox VE ISO, finished by Ansible, and given a
Packer-built template that management VMs are cloned from. The procedure is
[Build Management Plane](/docs/runbook/substrate/building-recovery/build-management-plane/).

Management VMs are created using **Ansible only** — simplicity and recoverability are prioritized over drift detection.
