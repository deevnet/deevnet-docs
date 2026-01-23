---
title: "Architecture"
weight: 1
bookCollapseSection: true
---

# Architecture

System-level design intent and contracts between layers.

---

## Two-Layer Model

Deevnet uses a **two-layer architecture** that separates infrastructure from workloads:

```
┌─────────────────────────────────────────────────────────┐
│                  Tenants (Workloads)                    │
│         grooveiq, vintronics, moneyrouter, etc.         │
└────────────────────────┬────────────────────────────────┘
                         │ runs on
┌────────────────────────▼────────────────────────────────┐
│              Substrate (Infrastructure)                 │
│     dvntm (mobile), dvnt (production)                   │
└─────────────────────────────────────────────────────────┘
```

### [Substrate](substrate/)

A **substrate** is an infrastructure environment—a self-contained network with
its own compute, storage, and management plane.

- **dvntm** — Mobile/portable lab for development, testing, and demos
- **dvnt** — Production home infrastructure (always-on, stable)

Each substrate operates independently and contains:
- [Networking](substrate/networking/) — Network segmentation and VLAN model
- [Management Plane](substrate/management-plane/) — Infrastructure control and DNS authority
- [Virtual Services](substrate/virtual-services/) — VM-based management services
- [Builder](substrate/builder/) — Bootstrap node and provisioning architecture

### [Tenant](tenant/)

A **tenant** is a logical workload namespace representing an application or
service domain.

Examples: `grooveiq`, `vintronics`, `moneyrouter`

Tenants live **on** substrates, not defining them:
- [Networking](tenant/networking/) — Tenant network isolation and VLAN model
- [Management](tenant/management/) — Tenant lifecycle and observability
- [Building](tenant/building/) — Tenant provisioning with Terraform

---

## Design Principles

### Substrate Independence

Each substrate (dvntm, dvnt) must be operable independently. No cross-substrate
dependencies for core functionality.

### Identity vs Intent

Hosts have **stable identity** (hostname, MAC, IP) that doesn't change when
workloads change. Workloads express **intent** and can move between hosts via
DNS CNAMEs.

### Air-Gapped Provisioning

Substrate infrastructure can be provisioned without upstream internet access.
The artifact server hosts all required images, packages, and configurations.

### Config-as-Code

All infrastructure configuration lives in version-controlled repositories:
- `ansible-inventory-deevnet` — Host identity and variables
- `ansible-collection-deevnet.builder` — Provisioning roles
- `ansible-collection-deevnet.mgmt` — Management plane and centralized services
- `ansible-collection-deevnet.net` — Network configuration
- `deevnet-image-factory` — OS image builds
