---
title: "Proxmox Hypervisors"
weight: 3
---

# Proxmox Hypervisors

## Purpose

Proxmox VE provides the **virtualization platform** for substrate workloads.  
In the dvntm architecture, Proxmox is used to host both **management-plane services**
and **tenant workloads**, with intentional separation between the two.

This separation reduces blast radius, improves recoverability, and keeps critical
infrastructure stable even during tenant experimentation or rebuilds.

---

## Hardware Specifications

| Attribute | Value |
|-----------|-------|
| **Quantity** | 2 hypervisors |
| **RAM** | 32 GB each |
| **Storage** | 1 TB each |
| **Proxmox Version** | PVE 8.4.1 |
| **Clustering** | Non-clustered (independent) |

### Hypervisor Roles

| Node | Role |
|-----|------|
| **Proxmox Node 1** | **Management Plane (`mgmt`)** |
| **Proxmox Node 2** | **Tenant Workloads** |

The management-plane hypervisor hosts infrastructure-critical services and follows
a slower, more deliberate change cadence. Tenant workloads are isolated to a
separate hypervisor to allow experimentation without risking platform stability.

---

## Network Position


```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│  Router/Gateway │◄────►│   Hypervisors    │◄────►│    Management VMs   │
│                 │      │                  │      │    Guest VMs        │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```


Proxmox hypervisors connect to the substrate network via OPNsense.  
Guest VMs receive network configuration from OPNsense DHCP, using static mappings
for known management-plane hosts.

---

## VM Templates

| Template | Description |
|----------|-------------|
| **Fedora** | Ansible-ready base image built via deevnet-image-factory |

Templates are built using Packer and stored locally on each hypervisor.  
New VMs clone from templates for rapid, consistent deployment.

---

## Workload Types

### Management Plane (mgmt)

Hosted on the dedicated management-plane hypervisor:

| Category | Examples |
|--------|----------|
| **Observability** | Metrics, logs, tracing, alerting |
| **Automation & CI** | Ansible runners, image factory helpers |
| **Access & recovery** | Jump hosts, OOB tooling |

> **Note**: Core network services (DNS, DHCP, NAT) run on the Core Router
> ([OPNsense](/docs/platforms/opnsense-router/) or [VyOS](/docs/platforms/vyos-router/)),
> not as VMs on the management hypervisor.

Management workloads are considered **infrastructure-critical** and must remain
available to support recovery and rebuild operations.

### Tenant Workloads

Hosted on the tenant hypervisor:

| Category | Examples |
|--------|----------|
| **Application development** | IoT backend, services, APIs |
| **Experiments** | Test environments, sandboxes |
| **Ephemeral workloads** | Short-lived or rebuildable VMs |

Tenant workloads tolerate higher churn and may be rebuilt frequently.

---

## Non-Clustered Design

The two hypervisors operate **independently** without Proxmox clustering:

| Aspect | Implication |
|--------|-------------|
| **No HA failover** | VMs do not automatically migrate on host failure |
| **No shared storage** | Each hypervisor uses local storage |
| **Independent management** | Each hypervisor has its own web UI |
| **Simpler operations** | No quorum concerns, no cluster networking |

### Rationale

For a two-node lab environment:
- Clustering adds complexity without meaningful HA
- Two-node clusters introduce quorum challenges
- Local storage is simpler and faster
- Manual VM placement is acceptable at this scale
- Future clustering remains possible with a third node

---

## Deterministic MAC Addressing

For **management-plane VMs**, network identity must be stable and reproducible.

### Policy

- Proxmox does **not** generate deterministic MAC addresses automatically
- All management-plane VMs explicitly define MAC addresses
- MACs are generated **outside Proxmox** and stored in inventory/code
- DHCP and DNS rely on these fixed MACs

See [MAC Namespace Specification](/docs/standards/mac-naming/) for the address
structure and [MAC Address Format](/docs/standards/mac-address-format/) for
formatting requirements.

This enables:
- Stable DHCP reservations
- Predictable IP addressing
- Safe VM rebuilds without network reconfiguration
- Clear mapping between hostnames, MACs, and roles

### Scope

| Workload Type | MAC Policy |
|--------------|-----------|
| **Management Plane** | Deterministic, inventory-defined |
| **Tenant Workloads** | May become deterministic later |

Deterministic MAC addressing for tenant workloads is deferred until tenant lifecycle
management is formalized.

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

### Management Plane

- Proxmox installation is currently **manual** (ISO + installer)
- Post-install configuration is performed via **Ansible**
- Management-plane VMs are created using **Ansible only**
- Simplicity and recoverability are prioritized over drift detection

Proxmox is treated as an API surface rather than a declarative state engine
for management workloads.

### Tenant Workloads (Future)

Tenant VM lifecycle management is expected to transition to **Terraform**:

| Capability | Purpose |
|-----------|---------|
| **Declarative VM definitions** | Reproducible tenant environments |
| **Drift detection** | Detect manual changes |
| **Lifecycle control** | Create, update, destroy per tenant |

Terraform will be introduced **only for tenant workloads**, avoiding unnecessary
complexity in the management plane.

---

## Future: Tenant Networking

Per [Roadmap item 9](/docs/roadmap/#9--proxmox-tenant-networking), VLAN-based tenant
isolation is planned:

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

1. **Two independent hosts**, intentionally role-separated
2. **Dedicated management-plane hypervisor** for critical services
3. **Non-clustered design** for operational simplicity
4. **Ansible-first provisioning** for management workloads
5. **Deterministic MAC addresses** for stable network identity
6. **Terraform planned** for future tenant lifecycle management
