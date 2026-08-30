---
title: "Networking"
weight: 1
---

# Tenant Networking

Defines the network isolation model for tenant workloads.

> The model on this page was established by
> [ADR-0001: Tenant Network Fabric]({{< relref "/docs/architecture/decisions/0001-tenant-network-fabric" >}}).
> It supersedes an earlier model in which the core router owned a physical VLAN, gateway, and
> DHCP scope for every tenant.

---

## Purpose

Tenant networking provides:
- **Isolation** — Tenants cannot see each other's traffic
- **Controlled access** — Explicit rules for shared services and the outside world
- **Scalability** — New tenants get a dedicated network with no physical reconfiguration
- **Security boundaries** — Limit blast radius of compromised workloads

---

## The tenant network is an overlay, owned by the tenant compute domain

A tenant network is a **virtual overlay**, not a physical VLAN. Its Layer 3 — the gateway,
routing, and isolation — is owned by the **tenant compute domain** (the tenant fabric), not by
the core router. Creating a tenant creates a virtual network; it does **not** require any change
to physical switching.

This keeps a clean line between physical and virtual:

- **Physical fabric** carries only an undifferentiated underlay between compute members.
- **Virtual fabric** holds all tenant structure — each tenant's subnet, gateway, and isolation
  boundary exist entirely in software and are defined in code.

Each tenant is an isolated routing domain. The gateway for a tenant's subnet lives in the tenant
fabric (an anycast gateway), so a tenant's default route never leaves the compute domain until it
reaches the perimeter.

---

## The tenant fabric

The **tenant fabric** is the logical tenant-network domain. It is currently realized on a single
tenant hypervisor (a **single-member fabric**) and is designed to expand to additional members
without redefinition — the boundary is the fabric, not any one host. See
[Tenant Hypervisors]({{< relref "/docs/platforms/tenant-compute/tenant-hypervisors" >}}) for the platform
realization and the single-node-to-cluster trajectory.

---

## Perimeter handoff

The tenant fabric hands off to the core router at a **perimeter transit boundary**. The core
router does not route between individual tenants and does not serve tenant DHCP; it sees only the
**transit network** and provides perimeter services on it:

| Function | Owned by |
|----------|----------|
| Tenant subnet, gateway, inter-tenant routing | Tenant fabric |
| Tenant isolation (per-tenant routing domains) | Tenant fabric |
| Tenant IPAM and DHCP | Tenant fabric |
| Outbound NAT / internet egress | Core router (perimeter) |
| Tenant ↔ management-plane policy | Core router (perimeter) |

Aggregate tenant egress leaves the fabric on the transit network; the core router applies
perimeter policy and NAT there.

---

## Tenant DNS Zones

Each tenant has a DNS zone scoped to its site:

```
tenant.site.deevnet.net
```

**Examples:**
- `grooveiq.dvntm.deevnet.net` — GrooveIQ on dvntm site
- `vintronics.dvnt.deevnet.net` — Vintronics on dvnt site

Services within a tenant use the pattern:
```
service.tenant.site.deevnet.net
```

**Examples:**
- `api.grooveiq.dvntm.deevnet.net`
- `db.grooveiq.dvntm.deevnet.net`

Internal tenant records are **owned by the tenant** and created as part of tenant provisioning,
then **published into the substrate zone** so tenant service names resolve consistently. This
aligns with the stateless-substrate model: rebuilding a tenant restores its own records.

---

## Inter-Tenant Routing

### Default Policy: Deny

Tenants cannot communicate with each other by default:
- Each tenant is a separate routing domain
- No routing between tenants
- Each tenant is an isolated security domain

### Explicit Allow

Cross-tenant communication requires explicit rules:
- Documented in IaC
- Reviewed for security implications
- Scoped to specific services and ports

---

## Access to Shared Services

Tenants may need access to substrate-level shared services. Access is granted at the perimeter,
from the tenant transit network to specific management-segment services:

| Service | Access Pattern |
|---------|----------------|
| **DNS** | Tenants → substrate DNS |
| **Internet** | Tenants → core router NAT (outbound only) |
| **Artifacts** | Tenants → artifact server (during provisioning) |
| **Observability** | Tenants → management plane (logs, metrics) |

---

## Per-Tenant Addressing and DHCP

Each tenant network has its own subnet, gateway, and DHCP scope, **served by the tenant fabric**:

- The tenant's gateway (`.1`) is the fabric's anycast gateway for that subnet
- IPAM and DHCP are owned by the fabric; the core router never learns tenant address space
- Static assignments may be used for tenant VMs with deterministic identity requirements

Tenant subnets, network identifiers, and routing-domain identifiers are allocated from a
**globally-unique** plan so that additional fabric members can join later without collision.

---

## Relationship to Substrate Networking

Tenant networking is a virtual layer on top of
[Substrate Networking]({{< relref "/docs/architecture/substrate/networking" >}}). The substrate provides the
physical underlay and the perimeter (core router); the tenant fabric provides the virtual tenant
networks that ride on top of it.

{{< mermaid >}}
graph TB
    subgraph tenant["Tenant Fabric (virtual overlay)"]
        T["tenant A, tenant B, tenant C — each an isolated routing domain"]
    end
    subgraph transit["Perimeter Transit"]
        X["aggregate tenant egress"]
    end
    subgraph substrate["Substrate (physical + perimeter)"]
        S["Core Router: NAT, internet, policy"]
    end
    tenant -->|egress via| transit
    transit -->|perimeter policy at| substrate
{{< /mermaid >}}

---

## Summary

1. A tenant network is a **virtual overlay** owned by the tenant fabric — not a physical VLAN
2. Tenant Layer 3 (gateway, routing, isolation, DHCP) lives in the tenant compute domain
3. The core router is the **perimeter**: NAT, internet egress, and tenant↔management policy on a
   transit network — it does not route between tenants
4. Default-deny between tenants; explicit allow in IaC
5. Tenant DNS follows `service.tenant.site.deevnet.net`, owned by the tenant and published to the
   substrate zone
6. Addressing and identifiers use a globally-unique plan so the fabric can grow to a cluster
