---
title: "Tenant"
weight: 5
bookCollapseSection: true
---

# Tenant Architecture

A **tenant** is a logical workload namespace representing an application or service domain,
**defined entirely as code** — its network, its workloads, and its DNS — so it can be rebuilt
from scratch against the substrate.

---

## What is a Tenant?

Tenants are the workload layer that runs **within** sites, on top of substrate infrastructure:

{{< mermaid >}}
graph TB
    subgraph tenants["Tenants (Workloads)"]
        T["grooveiq, vintronics, moneyrouter, etc."]
    end
    subgraph substrate["Substrate Infrastructure"]
        S["Network, Compute, Management Plane"]
    end
    tenants -->|deployed on| substrate
{{< /mermaid >}}

Examples of tenants: `grooveiq`, `vintronics`, `moneyrouter`

---

## Key Properties

### Tenants Live Within Sites

Tenants:
- Run **within** sites, not defining them
- May be deployed to one or more sites
- Are isolated from other tenants
- Share substrate infrastructure (network, compute, management)

### Tenant Networks Are Virtual Overlays

A tenant's network is a **virtual overlay owned by the tenant compute domain (the tenant fabric)**,
not a physical VLAN on the core router. The tenant owns its own Layer 3 — subnet, gateway, routing,
and isolation — while the core router acts only as the **perimeter** (NAT, internet egress, and
tenant↔management policy on a transit boundary). Creating a tenant creates a virtual network; it
requires **no change to physical switching**. This is the model established by
[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/); see
[Networking](/docs/architecture/tenant/networking/) for the full model.

### Code Is the Source of Truth

Every tenant supplies the **IaC and CaC** needed to rebuild itself from scratch against the
substrate, and it supplies them from **its own repository** — `deevnet-tenant-<name>`, not a
directory inside a substrate repo
([ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/)). Nothing about a tenant is precious hand-clicked state: its overlay network, its VMs,
and its DNS records are all declared in the tenant's own code. Rebuilding a tenant reconstitutes
it whole — network, workloads, and records — which is what keeps the substrate stateless and the
tenant portable.

### Intent Over Identity

Tenants express **intent** (what's running), not **identity** (what the host is):
- A host has stable identity (hostname, MAC, IP)
- A tenant workload can move between hosts
- Services are addressed by DNS, not by host

### DNS Naming Pattern

Tenant services follow a hierarchical DNS pattern:

```
service.tenant.site.deevnet.net
```

**Example:** `api.grooveiq.mobile.deevnet.net`
- `api` — the service
- `grooveiq` — the tenant
- `mobile` — the site
- `deevnet.net` — the domain

---

## Tenant vs Site

| Aspect | Site | Tenant |
|--------|------|--------|
| **Purpose** | Infrastructure boundary | Workload namespace |
| **Contains** | Network, compute, management | Applications, services |
| **Lifetime** | Long-lived, stable | May be created/destroyed frequently |
| **Provisioning** | Automation-first | Terraform-first |
| **Example** | `mobile`, `home` | `grooveiq`, `vintronics` |

---

## Multi-Site Tenants

A tenant may be deployed to multiple sites:

```
api.grooveiq.mobile.deevnet.net  — Development instance
api.grooveiq.home.deevnet.net   — Production instance
```

The tenant is logically the same (`grooveiq`), but instances are site-scoped.

---

## The Tenant Contract

A tenant is defined by the **contract** it satisfies with the substrate — a clean interface
between what the tenant supplies and what the substrate guarantees:

| The tenant supplies (as code) | The substrate guarantees |
|-------------------------------|--------------------------|
| Its overlay network (subnet, gateway, isolation) in the fabric | A tenant fabric to attach to |
| Its workloads (VMs from a template) | Compute on the tenant hypervisor |
| Its data disks, sized and attached to its VMs | VM images with a small, growable OS disk |
| Its own repository, from which it is rebuilt | A fabric attachment, issued at onboarding |
| Custody of its Terraform state, or use of the one offered | A state store it may use or decline |
| Its DNS records | A DNS zone to publish into |
| Its addressing, from a globally-unique plan | A perimeter for egress and shared-service access |

Because the interface is explicit, any conforming tenant can be built, rebuilt, or moved without
changing the substrate. The contract itself is being formalized — see the
[Tenant Platform roadmap](/docs/roadmap/infrastructure/mobile/tenant-platform/).

---

## Child Documents

- [Networking](/docs/architecture/tenant/networking/) — Tenant network isolation via the overlay fabric
- [Management](/docs/architecture/tenant/management/) — Tenant lifecycle and observability
- [Building](/docs/architecture/tenant/building/) — Tenant provisioning as code
