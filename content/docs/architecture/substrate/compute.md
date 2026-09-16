---
title: "Compute"
weight: 2
---

# Substrate Compute

Defines the virtualization and compute model for Deevnet sites.

---

## Overview

Compute infrastructure provides virtualization hosts for the management / control plane and for the workloads that run on the substrate. Hypervisors run within the substrate and host:

- **Management / control plane VMs**: one per domain
- **Workload VMs**: what runs on the substrate, described in [Tenant](/docs/architecture/tenant/)

---

## Compute Hosts

Each site includes one or more hypervisors that provide the virtualization layer. Compute hosts are provisioned through the builder and managed via the management plane.

| Role | Purpose |
|------|---------|
| Management hypervisor | Hosts the [management / control plane](/docs/architecture/substrate/management-plane/) domain VMs |
| Workload hypervisor | Hosts workload VMs |

---

## Architectural Properties

- Compute hosts are **stateless** — they can be reprovisioned from scratch via the builder
- VM placement is determined by role (management vs. workload), not by manual assignment
- All compute hosts receive static IP assignments in the management segment
