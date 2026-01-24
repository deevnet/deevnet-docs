---
title: "Tenant"
weight: 2
bookCollapseSection: true
---

# Tenant Architecture

A **tenant** is a logical workload namespace representing an application or service domain.

---

## What is a Tenant?

Tenants are the workload layer that runs **on top of** substrate infrastructure:

{{< mermaid >}}
graph TB
    subgraph tenants["Tenants (Workloads)"]
        T["grooveiq, vintronics, moneyrouter, etc."]
    end
    subgraph substrate["Substrate Infrastructure"]
        S["Network, Compute, Management Plane, Builder"]
    end
    tenants -->|runs on| substrate
{{< /mermaid >}}

Examples of tenants: `grooveiq`, `vintronics`, `moneyrouter`

---

## Key Properties

### Tenants Live On Substrates

Tenants:
- Run **on** substrates, not defining them
- May be deployed to one or more substrates
- Are isolated from other tenants
- Share substrate infrastructure (network, compute, management)

### Intent Over Identity

Tenants express **intent** (what's running), not **identity** (what the host is):
- A host has stable identity (hostname, MAC, IP)
- A tenant workload can move between hosts
- Services are addressed by DNS, not by host

### DNS Naming Pattern

Tenant services follow a hierarchical DNS pattern:

```
service.tenant.substrate.deevnet.net
```

**Example:** `api.grooveiq.dvntm.deevnet.net`
- `api` — the service
- `grooveiq` — the tenant
- `dvntm` — the substrate
- `deevnet.net` — the domain

---

## Tenant vs Substrate

| Aspect | Substrate | Tenant |
|--------|-----------|--------|
| **Purpose** | Infrastructure environment | Workload namespace |
| **Contains** | Network, compute, management | Applications, services |
| **Lifetime** | Long-lived, stable | May be created/destroyed frequently |
| **Provisioning** | Ansible-first (builder) | Terraform-first |
| **Example** | `dvntm`, `dvnt` | `grooveiq`, `vintronics` |

---

## Multi-Substrate Tenants

A tenant may be deployed to multiple substrates:

```
api.grooveiq.dvntm.deevnet.net  — Development instance
api.grooveiq.dvnt.deevnet.net   — Production instance
```

The tenant is logically the same (`grooveiq`), but instances are substrate-scoped.

---

## Child Documents

- [Networking](networking/) — Tenant network isolation and VLAN model
- [Management](management/) — Tenant lifecycle and observability
- [Building](building/) — Tenant provisioning with Terraform
