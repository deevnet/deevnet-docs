---
title: "Compute"
weight: 2
---

# Substrate Compute

Defines the virtualization and compute model for Deevnet sites.

---

## Overview

Compute infrastructure provides virtualization hosts for the management / control plane and for tenant workloads. Hypervisors run within the substrate and host:

- **Management / control plane VMs**: one per domain, holding substrate services or shared tenant services
- **Tenant application VMs**: workloads deployed by tenants

---

## Compute Hosts

Each site includes one or more hypervisors that provide the virtualization layer. Compute hosts are provisioned through the builder and managed via the management plane.

| Role | Purpose |
|------|---------|
| Management hypervisor | Hosts the [management / control plane](/docs/architecture/substrate/management-plane/) domain VMs |
| Tenant hypervisor | Hosts tenant application VMs |

---

## Architectural Properties

- Compute hosts are **stateless** — they can be reprovisioned from scratch via the builder
- VM placement is determined by role (management vs. tenant), not by manual assignment
- All compute hosts receive static IP assignments in the management segment
