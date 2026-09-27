---
title: "Management"
weight: 3
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

A tenant's whole lifecycle runs through the Deevnet API. The operator admits it once; everything
after that is the tenant's own ([Substrate and Tenant](/docs/architecture/tenant/boundary/)).

### Create

1. **Admission** — the operator registers the tenant's name, and the API issues a single-use
   enrollment token. This is the only substrate act in a tenant's life.
2. **First apply** — the tenant's first apply spends the token, and the API builds everything the
   tenant is entitled to, numbered from the index it allocates: the fabric overlay network, the
   DNS zone and its update key, a state store prefix, log partitions and their tokens, and a
   dashboards organization. It returns the tenant's own token.

No perimeter rule is added. The core router sees tenants only in aggregate, so a new tenant needs no
router or switch change ([Networking → Perimeter handoff](/docs/architecture/tenant/networking/#perimeter-handoff)).

### Update

Adding or removing workloads, names, Wi-Fi keys, devices and broker accounts is a
change the tenant applies from its own repository. None of it needs the operator.

### Destroy

1. **The tenant destroys its own resources** — workloads first. The API refuses to remove a tenant
   while it still has workloads.
2. **The tenant is deleted** — the API revokes its Wi-Fi keys and removes its dashboards, log
   tokens, network, DNS zone and resolver forwarding, and state store access, then its registry
   entry.

A tenant's index is never reused while that tenant exists.

---

## Tenant Observability

### Logs

Each tenant has its own partitions in the tenant log store, run by the control plane: workload logs,
and device logs arriving over MQTT. It writes and reads them with tokens of its own, and no other
tenant's token reaches them ([ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/)).

### Dashboards

Each tenant has a Grafana organization of its own, with its logs already wired in as data sources
([ADR-0024](/docs/architecture/decisions/0024-dashboards/)).

### Metrics and alerting

Tenants have no metrics store or alerting yet. The design is
[ADR-0023](/docs/architecture/decisions/0023-metrics-and-alerting/), and building it is part of the
[Tenant Platform](/docs/roadmap/infrastructure/mobile/tenant-platform/)
roadmap project.

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
- API tokens: the operator's, and one per tenant
- The SSH keys a tenant declares for its own workloads
- Zone policy on the core router, and the operator route into tenant networks
  ([ADR-0018](/docs/architecture/decisions/0018-operator-access-to-tenants/))

---

## Relationship to Substrate Management

Tenant management is distinct from substrate management:

| Aspect | Substrate Management | Tenant Management |
|--------|---------------------|-------------------|
| **Scope** | Infrastructure (router, hypervisors) | Workloads (VMs, applications) |
| **Tooling** | Procedural configuration | Declarative, through the API |
| **Lifecycle** | Rare changes, high stability | Frequent changes, agile |
| **Authority** | Platform admins only | May delegate to tenant admins |

The substrate's [Shared Tenant Services](/docs/architecture/tenant/shared-services/)
provide what tenants consume (DNS zone, state store, observability), and the core network provides
the perimeter for tenant egress. Tenant addressing is owned by the tenant fabric, not the core router.

---

## Tenant Isolation Principles

### Blast Radius Containment

A problem in one tenant should not affect others:
- Network isolation via the tenant fabric (per-tenant routing domains)
- Independent lifecycle

There are no per-tenant resource quotas: one tenant's workloads can use up the tenant hypervisor.
Quotas are on the [Tenant Platform](/docs/roadmap/infrastructure/mobile/tenant-platform/)
roadmap.

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

The procedures are in the runbook: [Tenant Admission](/docs/runbook/substrate/tenant-admission/)
for the operator's side, and [Tenant Operations](/docs/runbook/tenant/) for everything a tenant does
itself.

---

## Summary

1. Tenants have explicit lifecycle: create, update, destroy
2. Observability (logs, metrics, alerts) is scoped per tenant
3. Access control separates platform admins from tenant admins
4. Tenant management is distinct from substrate management
5. Isolation principles prevent cross-tenant impact
