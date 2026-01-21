---
title: "Tenant Compute"
weight: 3
bookCollapseSection: true
---

# Tenant Compute

The **tenant compute layer** provides resources for application workloads, experiments, and user-facing services. Unlike the control plane, tenant compute is designed for higher churn and experimentation.

---

## Tenant Compute Components

| Component | Purpose |
|-----------|---------|
| **Tenant Hypervisors** | Proxmox hosts for VM-based tenant workloads |
| **Raspberry PIs** | Edge/IoT compute for specialized workloads |

---

## Characteristics

Tenant compute infrastructure is:

- **Tolerant of rebuilds** — Expect frequent provisioning and teardown
- **Fast change cadence** — Experimentation and iteration encouraged
- **Terraform-managed** — Declarative VM lifecycle (future)
- **VLAN-isolated** — Tenant traffic separated from management plane

---

## Workload Types

| Category | Examples |
|----------|----------|
| **Application development** | IoT backend, services, APIs |
| **Experiments** | Test environments, sandboxes |
| **Ephemeral workloads** | Short-lived or rebuildable VMs |
| **Edge/IoT** | Sensor collection, local processing |

---

## Separation from Control Plane

Tenant compute is deliberately separated from control plane infrastructure:

| Aspect | Control Plane | Tenant Compute |
|--------|---------------|----------------|
| **Change cadence** | Slow, deliberate | Fast, experimental |
| **Blast radius** | Must be minimized | Tolerable |
| **Rebuild tolerance** | Low — avoid rebuilds | High — expect rebuilds |
| **Provisioning** | Ansible | Terraform (future) |

This separation ensures that tenant experimentation cannot impact substrate stability. If a tenant VM misbehaves or a tenant hypervisor fails, the control plane remains operational.

---

## Future: VLAN Isolation

Per the roadmap, VLAN-based tenant isolation is planned:

| Feature | Description |
|---------|-------------|
| **VLAN tagging** | Each tenant gets a dedicated VLAN |
| **Core Router integration** | Inter-VLAN routing and firewall rules |
| **Network isolation** | Tenants cannot see each other's traffic |
| **Per-tenant DHCP** | Separate address pools per VLAN |
