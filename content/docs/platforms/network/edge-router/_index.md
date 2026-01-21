---
title: "Edge Router"
weight: 1
---

# Edge Router

## Purpose

The edge router provides **upstream connectivity** between the substrate and the external network (ISP, travel router, or host network).

---

## Hardware

| Substrate | Hardware | Notes |
|-----------|----------|-------|
| **dvntm** | Travel router | Portable WAN for mobile substrate |
| **dvnt** | ISP router | Home internet connection |

### Selection Rationale

TBD — Hardware selection depends on deployment context. The edge router is typically provided by the ISP or selected for portability in mobile deployments.

---

## Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | Varies (ISP-provided or travel router firmware) |
| **Version** | N/A |

### Automation Capability

- Edge routers are typically **not automated** — they are treated as opaque upstream connectivity
- Configuration is manual or vendor-managed
- The substrate assumes the edge router provides DHCP on its LAN interface (for bootstrap node upstream connectivity)

---

## Roles

The edge router provides:

| Role | Description |
|------|-------------|
| **WAN connectivity** | Routes substrate traffic to the internet |
| **NAT** | Masquerades substrate traffic behind a public IP |
| **DHCP (upstream)** | Provides IP to the bootstrap node's upstream interface |

---

## Relationship to Substrate

The edge router is **external** to the substrate — it provides connectivity but is not managed by Deevnet automation. The Core Router handles all internal routing and services.

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│   Edge Router   │◄────►│   Core Router    │◄────►│  Substrate Hosts    │
│   (unmanaged)   │      │   (managed)      │      │                     │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
```
