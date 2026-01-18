---
title: "Networking"
weight: 1
---

# Tenant Networking

Defines the network isolation model for tenant workloads.

---

## Purpose

Tenant networking provides:
- **Isolation** — Tenants cannot see each other's traffic
- **Controlled access** — Explicit rules for shared services
- **Scalability** — New tenants get dedicated network segments
- **Security boundaries** — Limit blast radius of compromised workloads

---

## VLAN Isolation Model

Each tenant receives a dedicated VLAN:

| Tenant | VLAN ID | Subnet | Purpose |
|--------|---------|--------|---------|
| `grooveiq` | 100 | 10.100.0.0/24 | IoT backend services |
| `vintronics` | 101 | 10.101.0.0/24 | Electronics projects |
| `moneyrouter` | 102 | 10.102.0.0/24 | Financial tracking |

VLAN IDs and subnets are assigned from a reserved range to avoid conflicts
with substrate segments (Management, Trusted, Storage, IoT, Guest).

---

## Tenant DNS Zones

Each tenant has a DNS zone scoped to its substrate:

```
tenant.substrate.deevnet.net
```

**Examples:**
- `grooveiq.dvntm.deevnet.net` — GrooveIQ on dvntm substrate
- `vintronics.dvnt.deevnet.net` — Vintronics on dvnt substrate

Services within a tenant use the pattern:
```
service.tenant.substrate.deevnet.net
```

**Examples:**
- `api.grooveiq.dvntm.deevnet.net`
- `db.grooveiq.dvntm.deevnet.net`
- `web.vintronics.dvnt.deevnet.net`

---

## Inter-Tenant Routing

### Default Policy: Deny

Tenants cannot communicate with each other by default:
- No routing between tenant VLANs
- Firewall blocks cross-tenant traffic
- Each tenant is an isolated security domain

### Explicit Allow

Cross-tenant communication requires explicit firewall rules:
- Documented in IaC
- Reviewed for security implications
- Scoped to specific services and ports

---

## Access to Shared Services

Tenants may need access to substrate-level shared services:

| Service | Access Pattern |
|---------|----------------|
| **DNS** | All tenants → Core Router DNS |
| **Internet** | All tenants → NAT gateway (outbound only) |
| **Artifacts** | Tenants → artifact server (during provisioning) |
| **Observability** | Tenants → management plane (logs, metrics) |

Access is granted via firewall rules from tenant VLANs to specific
management segment services.

---

## Per-Tenant DHCP

Each tenant VLAN has its own DHCP scope:

| Tenant | DHCP Range | Gateway |
|--------|------------|---------|
| `grooveiq` | 10.100.0.100-200 | 10.100.0.1 |
| `vintronics` | 10.101.0.100-200 | 10.101.0.1 |
| `moneyrouter` | 10.102.0.100-200 | 10.102.0.1 |

The Core Router serves DHCP for all tenant VLANs via its VLAN interfaces.

Static DHCP reservations may be used for tenant VMs with deterministic
identity requirements.

---

## Relationship to Substrate Networking

Tenant networking is a layer on top of [Substrate Networking](/docs/architecture/substrate/networking/):

```
┌─────────────────────────────────────────────────────────┐
│              Tenant VLANs (per-tenant)                  │
│     grooveiq (100), vintronics (101), etc.              │
└────────────────────────┬────────────────────────────────┘
                         │ isolated from
┌────────────────────────▼────────────────────────────────┐
│           Substrate Segments (shared)                   │
│   Management, Trusted, Storage, IoT, Guest              │
└─────────────────────────────────────────────────────────┘
```

Tenant VLANs:
- Use the same Core Router for routing and firewall
- Share physical switch infrastructure (802.1Q trunking)
- Are isolated from substrate management traffic

---

## Core Router Integration

The Core Router provides tenant networking via:

| Function | Implementation |
|----------|----------------|
| **VLAN interfaces** | One sub-interface per tenant |
| **DHCP scopes** | Per-tenant address pools |
| **Firewall zones** | Per-tenant security zones |
| **NAT** | Outbound NAT for all tenants |
| **DNS forwarding** | Tenant queries to upstream or authoritative |

---

## Future: Tenant Self-Service

Planned capabilities for tenant networking:

- Tenant-defined internal DNS records
- Tenant-scoped firewall rule requests
- Bandwidth and QoS policies per tenant
- Tenant network dashboards

These are tracked in the [Roadmap](/docs/roadmap/).

---

## Summary

1. Each tenant gets a dedicated VLAN for isolation
2. Default-deny routing between tenants
3. DNS follows `service.tenant.substrate.deevnet.net` pattern
4. Per-tenant DHCP scopes from Core Router
5. Access to shared services via explicit firewall rules
