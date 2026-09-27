---
title: "Tenant Hypervisors"
weight: 1
bookCollapseSection: true
---

# Tenant Hypervisors

Fills the **tenant hypervisor** role — see [Substrate Compute → Compute by purpose](/docs/architecture/substrate/compute/#compute-by-purpose).
The host is `dv02hyp002p02`.

---

## Hardware

[Dell OptiPlex 7060 Micro](/docs/platforms/hardware/compute/dell-optiplex-7060-mff/): specs, cabling, power and console.

### Requirements

| Attribute | Requirement | Rationale |
|-----------|-------------|-----------|
| **RAM** | 32GB minimum | Multiple tenant VMs |
| **Storage** | 1TB SSD | VM images, local storage |
| **CPU** | Modern x86_64 with VT-x | Virtualization support |
| **NICs** | Gigabit Ethernet | Substrate network connectivity |

---

## Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | Proxmox VE |
| **Version** | [Software Catalog](/docs/platforms/software-catalog/#tenant-hypervisor-dv02hyp002p02) |
| **Base** | Debian |

### Automation Capability

- **Installation**: manual, from the standard Proxmox VE ISO ([Build a Hypervisor](/docs/runbook/substrate/building-recovery/build-hypervisor/)). An unattended ISO is [unfinished work](/docs/roadmap/infrastructure/mobile/builder/) in `deevnet-image-factory`
- **Post-install**: Ansible: `deevnet.builder` (node baseline, storage) and `deevnet.net` (`proxmox_node_network`: the bridge, transit routing and tenant egress)
- **VM provisioning**: the Deevnet API, on behalf of each tenant's Terraform
- **Templates**: Packer-built Fedora templates stored locally

---

## VM Templates

| Template | Description |
|----------|-------------|
| **Fedora** | Ansible-ready base image built via deevnet-image-factory |

Templates are built using Packer and stored locally on each hypervisor. New VMs clone from templates for rapid, consistent deployment.

### Build-time addressing

The build VM takes a **pinned address**, `10.20.99.79` on the management segment,
rather than a DHCP lease. It is not a reserved host: the address exists only for
the duration of a build.

This is deliberate. The installer needs an address before it can fetch its
kickstart, and the installed system needs one for Packer's SSH provisioner. If
that came from DHCP, building an image would depend on a substrate service being
healthy — and when DHCP is unavailable the build does not fail quickly or
clearly. It boots, waits, and drops into a dracut emergency shell roughly seven
minutes later reporting *"missing inst.stage2 or inst.repo"*, which points at the
install source rather than at the network. That is an expensive way to learn the
DHCP pool is down.

Pinning the address means an image build either succeeds or fails for reasons
inside the build.

**It does not reach clones.** The last step of the build removes the
NetworkManager connection profile along with `machine-id` and the SSH host keys,
so a clone inherits no address, no identity, and no host keys. Tenant workloads
are addressed by cloud-init from the tenant fabric — see
[Tenant Fabric](/docs/platforms/tenant-compute/tenant-hypervisors/tenant-fabric/).

`10.20.99.79` sits in the `.70-.79` experimental/lab range of the
[addressing plan](/docs/architecture/naming-and-addressing/#host-addressing-ranges), clear of both the `.2-.49`
static infrastructure range and the `.200-.230` DHCP pool. Override with
`build_ip`, or set `build_use_dhcp=true` to go back to a lease.

---

## Provisioning

Tenant workloads are declared by each tenant in Terraform through the `deevnet/deevnet` provider
and built by the Deevnet API; the management plane stays on Ansible. See
[Tenant Operations](/docs/runbook/tenant/).

---

## Non-Clustered Design

The node is a standalone Proxmox host, not a cluster member: no HA manager, no shared storage, and
its own web UI. Why is in
[Substrate Compute → Nothing is clustered](/docs/architecture/substrate/compute/#nothing-is-clustered);
how the fabric is built to gain a second member later is in [Tenant Fabric (SDN)](tenant-fabric/).

---

## Tenant Networking

The tenant network model is in [Tenant Networking](/docs/architecture/tenant/networking/). This node
implements it with Proxmox SDN — see [Tenant Fabric (SDN)](tenant-fabric/).

---

## Deterministic MAC Addressing

Tenant workload MACs are **derived by the Deevnet API** from the tenant's index, like the rest of a
tenant's identifiers ([Tenant → The Tenant Contract](/docs/architecture/tenant/#the-tenant-contract)).
Management-hypervisor VMs follow the inventory-defined policy on the
[Management Hypervisor](/docs/platforms/management-plane/management-hypervisor/#deterministic-mac-addressing).
