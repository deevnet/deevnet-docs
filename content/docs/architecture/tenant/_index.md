---
title: "Tenant"
weight: 3
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
        T["eds · tdemo"]
    end
    subgraph substrate["Substrate Infrastructure"]
        S["Network · Compute · Management Plane · Control Plane"]
    end
    tenants -->|deployed on| substrate
{{< /mermaid >}}

The tenants that exist today are **`eds`** — the LP jacket stand application, whose workload drives
an RGB strip from album cover art — and **`tdemo`**, the reference tenant a new tenant is copied
from.

---

## Key Properties

### Tenants Live Within Sites

Tenants:
- Run **within** sites, not defining them
- May be deployed to one or more sites
- Are isolated from other tenants
- Share substrate infrastructure (network, compute, and both planes)

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
([ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/)). Nothing about a tenant is
precious hand-clicked state: its workloads and the names in front of them are declared in the
tenant's own code, and the network they land on is built for it by the control plane from that same
declaration. Rebuilding a tenant reconstitutes it whole — network, workloads, and records — which
is what keeps the substrate stateless and the tenant portable.

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

**Example:** `service.eds.mobile.deevnet.net`
- `service` — the service
- `eds` — the tenant
- `mobile` — the site
- `deevnet.net` — the domain

---

## Tenant vs Site

| Aspect | Site | Tenant |
|--------|------|--------|
| **Purpose** | Infrastructure boundary | Workload namespace |
| **Contains** | Network, compute, management and control planes | Applications, services |
| **Lifetime** | Long-lived, stable | May be created/destroyed frequently |
| **Provisioning** | Automation-first | Terraform-first |
| **Example** | `mobile` | `eds`, `tdemo` |

---

## Multi-Site Tenants

A tenant may be deployed to multiple sites. The name is logically the same; the instances are
site-scoped and independent:

```
service.eds.mobile.deevnet.net   — the instance that exists
service.eds.home.deevnet.net     — what a second instance would be called
```

Only `mobile` is built today; `home` is a reserved zone
([Limits](/docs/policies/risk-management/resiliency/)). Each instance would be built separately, against that
site's own substrate, from the same tenant repository.

---

## The Tenant Contract

A tenant is defined by the **contract** it satisfies with the substrate — a clean interface between
what the tenant declares and what the substrate builds for it.

The line between those two moved with
[ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/). A tenant used to
declare its own network, derive every identifier from an index it was issued, and hold a Proxmox
credential to build with. It now **asks the Deevnet API**, and the API builds all of that on its
behalf. The tenant is left declaring only what is genuinely its own:

| The tenant declares | The substrate builds and guarantees |
|---------------------|--------------------------------------|
| That it exists, and its name | Its index, and every identifier derived from it — VRF, VNet, subnet, gateway |
| Its workloads: how many, how big, whose SSH keys | The VMs, their VMIDs, MACs and addresses, on the tenant hypervisor |
| The names it wants in front of them | A delegated DNS zone, and the key that writes into it |
| Whether to use the offered state store | An S3-compatible state store it may use or decline |
| Its own repository, from which it is rebuilt | A perimeter for egress and shared-service access |

Two properties of that interface matter more than the rows themselves:

- **A tenant holds no substrate credential.** It is admitted with a single-use enrollment token and
  trades it for its own token on first apply. It never holds a Proxmox login, a vault password or a
  controller credential — so there is nothing it could use to reach around the interface.
- **Nothing recurring needs a substrate commit.** Onboarding a tenant is a substrate act;
  everything after it — adding a workload, publishing a name, issuing a device key — is the
  tenant's own `terraform apply`
  ([ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/)).

Because the interface is explicit, any conforming tenant can be built, rebuilt, or moved without
changing the substrate. See [Building](/docs/architecture/tenant/building/) for what that looks
like in practice.

---

## Child Documents

- [Networking](/docs/architecture/tenant/networking/) — Tenant network isolation via the overlay fabric
- [Shared Tenant Services](/docs/architecture/tenant/shared-services/) — Substrate-run services tenants consume, and the rules for consuming them
- [Management](/docs/architecture/tenant/management/) — Tenant lifecycle and observability
- [Building](/docs/architecture/tenant/building/) — Tenant provisioning as code
