---
title: "Proxmox Hypervisors"
weight: 3
---

# Proxmox Hypervisors

## Purpose

Proxmox VE provides the **virtualization platform** for substrate workloads. These hypervisors host VMs for infrastructure automation, application development, and tenant workloads.

---

## Hardware Specifications

| Attribute | Value |
|-----------|-------|
| **Quantity** | 2 hypervisors |
| **RAM** | 32 GB each |
| **Storage** | 1 TB each |
| **Proxmox Version** | PVE 8.4.1 |
| **Clustering** | Non-clustered (independent) |

---

## Network Position

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│    OPNsense     │◄────►│    Proxmox       │◄────►│    Guest VMs        │
│  Router/Gateway │      │   Hypervisors    │      │                     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```

Proxmox hypervisors connect to the substrate network via OPNsense. Guest VMs receive network configuration from OPNsense DHCP (static mappings for known hosts).

---

## Current Capabilities

### VM Templates

| Template | Description |
|----------|-------------|
| **Fedora** | Ansible-ready base image built via deevnet-image-factory |

Templates are built using Packer and stored locally on each hypervisor. New VMs clone from templates for rapid deployment.

### Workload Types

| Category | Examples |
|----------|----------|
| **Infrastructure automation** | OPNsense VM, test environments, CI runners |
| **Application development** | Tenant workloads, iot-backend, dev/test VMs |

---

## Non-Clustered Design

The two hypervisors operate **independently** without Proxmox clustering:

| Aspect | Implication |
|--------|-------------|
| **No HA failover** | VMs don't automatically migrate on host failure |
| **No shared storage** | Each hypervisor uses local storage |
| **Independent management** | Each hypervisor has its own web UI |
| **Simpler operations** | No quorum concerns, no cluster networking |

### Rationale

For a lab environment with two nodes:
- Clustering adds complexity without meaningful HA (two-node clusters have quorum issues)
- Local storage is simpler and faster than shared storage
- Manual VM placement is acceptable at this scale
- Future clustering remains possible if a third node is added

---

## VM Template Workflow

Templates are built via the **deevnet-image-factory** repository:

1. **Packer builds** create base images with cloud-init
2. **Ansible provisioning** applies baseline configuration
3. **Template export** creates Proxmox-compatible images
4. **Local import** stores templates on each hypervisor

VMs cloned from templates are immediately ready for Ansible management.

---

## Provisioning

### Current State

Proxmox installation is currently **manual**:
- ISO boot and interactive installer
- Post-install configuration via Ansible

### Future: Automated Installation

Per [Roadmap item 7](/docs/roadmap/#7--proxmox-installation), automated Proxmox provisioning is planned:
- PXE boot from bootstrap node
- Kickstart/preseed for unattended install
- Ansible post-configuration

---

## Future: Tenant Networking

Per [Roadmap item 9](/docs/roadmap/#9--proxmox-tenant-networking), VLAN-based tenant isolation is planned:

| Feature | Description |
|---------|-------------|
| **VLAN tagging** | Each tenant gets a dedicated VLAN |
| **OPNsense integration** | Inter-VLAN routing and firewall rules |
| **Network isolation** | Tenants cannot see each other's traffic |
| **Per-tenant DHCP** | Separate address pools per VLAN |

---

## Relationship to Other Docs

| Document | Relationship |
|----------|--------------|
| [Bootstrap Node](/docs/architecture/bootstrap-node/) | Provisions and configures Proxmox hosts |
| [OPNsense Router](/docs/architecture/opnsense-router/) | Provides networking for Proxmox and guest VMs |
| [Roadmap: Proxmox Installation](/docs/roadmap/#7--proxmox-installation) | Automated provisioning (planned) |
| [Roadmap: Tenant Networking](/docs/roadmap/#9--proxmox-tenant-networking) | VLAN isolation (planned) |

---

## Summary

Proxmox hypervisors provide the virtualization foundation for Deevnet:

1. **Two independent hosts** — 32 GB RAM, 1 TB storage each
2. **Non-clustered** — Simplicity over HA for lab scale
3. **Fedora template** — Ansible-ready VMs from deevnet-image-factory
4. **Infrastructure + application** — Hosts both automation and tenant workloads
5. **Future VLAN support** — Tenant network isolation via OPNsense
