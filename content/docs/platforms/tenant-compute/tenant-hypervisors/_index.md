---
title: "Tenant Hypervisors"
weight: 1
bookCollapseSection: true
---

# Tenant Hypervisors

## Purpose

The tenant hypervisors host **application workloads and experiments**. This is Proxmox Node 2 in the two-hypervisor architecture, dedicated to workloads that may be rebuilt frequently and can tolerate higher churn.

---

## Hardware

| Substrate | Hardware | Notes |
|-----------|----------|-------|
| **dvntm** | Dell Optiplex 7050 MFF | Repurposed enterprise desktop |
| **dvnt** | TBD | Desktop or rack-mounted server |

### Selection Rationale

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
| **Version** | PVE 8.4.1 |
| **Base** | Debian 12 (Bookworm) |

### Automation Capability

- **Installation**: Manual ISO install (no PXE support for Proxmox)
- **Post-install**: Ansible configuration via `deevnet.builder` collection
- **VM provisioning**: Terraform (future) for declarative lifecycle
- **Templates**: Packer-built Fedora templates stored locally

---

## Dell Optiplex 7050 MFF

**Substrate**: dvntm (mobile)

The Dell Optiplex 7050 Micro Form Factor is a repurposed enterprise desktop used as the tenant hypervisor for the mobile substrate. Its compact size, low power consumption, and Intel virtualization support make it well-suited for always-on infrastructure workloads.

![Dell Optiplex 7050 MFF](dell-optiplex-7050-mff.jpg)

### Hardware

| Attribute | Value |
|-----------|-------|
| **Model** | Dell Optiplex 7050 Micro Form Factor |
| **CPU** | Intel i7-6700T (4-core/8-thread, 2.8-3.6GHz, 35W TDP) |
| **Memory** | 32GB DDR4 |
| **Storage** | 1TB NVMe/SATA SSD |
| **Ethernet** | 1x Gigabit (Intel I219-LM) |
| **Form factor** | Micro Form Factor (MFF) |
| **Power** | ~35W TDP |

### Selection Rationale

- **Repurposed enterprise desktop** - reliable, well-supported hardware
- **32GB RAM** meets tenant hypervisor requirements for multiple VMs
- **Compact form factor** suitable for mobile lab placement
- **Low power consumption** for always-on operation
- **Intel VT-x/VT-d** for Proxmox virtualization support
- **Intel I219-LM NIC** for reliable network connectivity

---

## Roles

The tenant hypervisor hosts these workload categories:

| Category | Examples |
|----------|----------|
| **Application development** | IoT backend, services, APIs |
| **Experiments** | Test environments, sandboxes |
| **Ephemeral workloads** | Short-lived or rebuildable VMs |

Tenant workloads tolerate higher churn and may be rebuilt frequently.

---

## VM Templates

| Template | Description |
|----------|-------------|
| **Fedora** | Ansible-ready base image built via deevnet-image-factory |

Templates are built using Packer and stored locally on each hypervisor. New VMs clone from templates for rapid, consistent deployment.

---

## Provisioning: Terraform (Future)

Tenant VM lifecycle management is expected to transition to **Terraform**:

| Capability | Purpose |
|-----------|---------|
| **Declarative VM definitions** | Reproducible tenant environments |
| **Drift detection** | Detect manual changes |
| **Lifecycle control** | Create, update, destroy per tenant |

Terraform will be introduced **only for tenant workloads**, avoiding unnecessary complexity in the management plane.

---

## Non-Clustered Design

The tenant hypervisor operates **independently** without Proxmox clustering:

| Aspect | Implication |
|--------|-------------|
| **No HA failover** | VMs do not automatically migrate |
| **No shared storage** | Local storage only |
| **Independent management** | Dedicated web UI |
| **Simpler operations** | No quorum concerns |

### Rationale

For a two-node lab environment:
- Clustering adds complexity without meaningful HA
- Two-node clusters introduce quorum challenges
- Local storage is simpler and faster
- Manual VM placement is acceptable at this scale

---

## Network Position

```
┌─────────────────┐      ┌────────────────────┐      ┌─────────────────────┐
│  Core Router    │◄────►│ Tenant             │◄────►│  Tenant VMs         │
│                 │      │ Hypervisor         │      │  (apps, experiments,│
│                 │      │ (Proxmox Node 2)   │      │   sandboxes)        │
└─────────────────┘      └────────────────────┘      └─────────────────────┘
```

Guest VMs receive network configuration from Core Router DHCP.

---

## Future: VLAN Isolation

When tenant networking is implemented:

| Feature | Description |
|---------|-------------|
| **VLAN tagging** | Each tenant gets a dedicated VLAN |
| **Core Router integration** | Inter-VLAN routing and firewall rules |
| **Network isolation** | Tenants cannot see each other's traffic |
| **Per-tenant DHCP** | Separate address pools per VLAN |

---

## Deterministic MAC Addressing

### Current Policy

Deterministic MAC addressing for tenant workloads is **deferred** until tenant lifecycle management is formalized.

| Workload Type | MAC Policy |
|--------------|-----------|
| **Management Plane** | Deterministic, inventory-defined |
| **Tenant Workloads** | TBD — may become deterministic later |
