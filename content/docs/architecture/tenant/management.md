---
title: "Management"
weight: 2
---

# Tenant Management

Defines the lifecycle and operational model for tenant workloads.

---

## Purpose

Tenant management provides:
- **Lifecycle control** — Create, update, and destroy tenant environments
- **Observability** — Logs, metrics, and alerting scoped to tenants
- **Access control** — Who can manage which tenants
- **Operational clarity** — Clear boundaries between tenants

---

## Tenant Lifecycle

### Create

Creating a new tenant involves:

1. **Reserve VLAN and subnet** — Allocate from tenant IP range
2. **Configure Core Router** — Add VLAN interface, DHCP scope, firewall zone
3. **Create DNS zone** — Add `tenant.substrate.deevnet.net` zone
4. **Provision VMs** — Deploy tenant workloads via Terraform
5. **Configure observability** — Set up log/metric collection for tenant

### Update

Updating a tenant may include:
- Adding or removing VMs
- Changing resource allocations
- Updating firewall rules
- Modifying DNS records

Updates are applied via Terraform for VMs, Ansible for network configuration.

### Destroy

Destroying a tenant:

1. **Destroy VMs** — Terraform destroys all tenant workloads
2. **Remove DNS records** — Clean up tenant zone
3. **Remove network config** — Delete VLAN, DHCP scope, firewall zone
4. **Archive data** — Backup logs and metrics if required
5. **Release resources** — Return VLAN ID and subnet to pool

---

## Tenant Observability

### Logs

Tenant logs are:
- Collected by management plane observability stack
- Tagged with tenant identifier
- Queryable by tenant scope
- Retained per tenant policy

### Metrics

Tenant metrics include:
- VM resource utilization (CPU, memory, disk, network)
- Application-level metrics (if instrumented)
- Network traffic volumes

### Alerting

Alerts may be configured:
- Per-tenant thresholds
- Tenant-specific notification channels
- Escalation policies

---

## Access Control

### Tenant Boundaries

Each tenant is an isolated security domain:
- No cross-tenant network access by default
- Separate credentials and access paths
- Independent lifecycle management

### Administrative Access

| Role | Access |
|------|--------|
| **Platform admin** | All tenants, substrate infrastructure |
| **Tenant admin** | Specific tenant(s), scoped access |

Access is controlled via:
- SSH key distribution
- Jump host access policies
- Firewall rules

---

## Relationship to Substrate Management

Tenant management is distinct from substrate management:

| Aspect | Substrate Management | Tenant Management |
|--------|---------------------|-------------------|
| **Scope** | Infrastructure (router, hypervisors) | Workloads (VMs, applications) |
| **Tooling** | Ansible-first | Terraform-first |
| **Lifecycle** | Rare changes, high stability | Frequent changes, agile |
| **Authority** | Platform admins only | May delegate to tenant admins |

The substrate [Management Plane](/docs/architecture/substrate/management-plane/)
provides services that tenants consume (DNS, DHCP, observability).

---

## Tenant Isolation Principles

### Blast Radius Containment

A problem in one tenant should not affect others:
- Network isolation via VLANs
- Resource quotas (future)
- Independent lifecycle

### No Shared State

Tenants do not share:
- Databases
- File storage
- Credentials
- Configuration

Shared services (DNS, NAT) are substrate-level, not tenant-level.

### Explicit Dependencies

If a tenant depends on another service:
- Document the dependency
- Create explicit firewall rules
- Monitor the dependency path

---

## Operational Runbooks

Common tenant operations:

| Operation | Runbook |
|-----------|---------|
| Create new tenant | Reserve VLAN, configure router, deploy VMs |
| Add VM to tenant | Update Terraform, apply, verify |
| Debug tenant network | Check VLAN, DHCP, firewall rules |
| Investigate tenant issue | Query tenant-scoped logs and metrics |
| Decommission tenant | Destroy VMs, clean up network, archive data |

---

## Summary

1. Tenants have explicit lifecycle: create, update, destroy
2. Observability (logs, metrics, alerts) is scoped per tenant
3. Access control separates platform admins from tenant admins
4. Tenant management is distinct from substrate management
5. Isolation principles prevent cross-tenant impact
