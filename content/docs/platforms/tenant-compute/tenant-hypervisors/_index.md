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
| **dvntm** | 32GB RAM, 1TB storage | Portable mini PC or NUC-style |
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
