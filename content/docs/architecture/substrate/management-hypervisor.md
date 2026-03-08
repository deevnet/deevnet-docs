---
title: "Management Hypervisor"
weight: 3
---

# Management Hypervisor Architecture

### Purpose

This document defines the **virtual management services** layer within the Deevnet management plane.

Virtual management services run on a dedicated hypervisor and provide observability, automation, and access tooling. They are **additive** to the Core Platform—the substrate functions without them, using only the Core Router and Bootstrap Node.

These services may be rebuilt entirely from the physical layer. If the management hypervisor is lost, core provisioning and network services remain operational.

For the core management plane architecture (DNS authority, naming, provisioner role, OOB services), see [Management Plane](../management-plane/).

---

## 1. Service Overview

Services that run as VMs on the dedicated management hypervisor:

| Service | Description |
|---------|-------------|
| **Observability** | Metrics collection, log aggregation, alerting |
| **Automation** | Ansible runners, image factory helpers |
| **Access** | Jump hosts, out-of-band tooling |

---

## 2. Platform Placement

Virtual management services run on a **dedicated Proxmox hypervisor**.

| Attribute | Value |
|---------|------|
| **Hypervisor role** | Management Plane |
| **Workload type** | Infrastructure-critical |
| **Change cadence** | Slow and deliberate |
| **Blast radius** | Isolated from tenants |

This separation ensures:
- Tenant rebuilds cannot disrupt core services
- Observability and access remain available during failures
- Platform recovery paths are always reachable

---

## 3. Design Principles

Virtual management services follow a strict set of principles:

- **Stability over velocity**
- **Explicit configuration over convenience**
- **Recoverability over optimization**
- **Isolation from tenant experimentation**

The management hypervisor is intentionally boring. That is a feature.

---

## 4. Service Characteristics

| Attribute | Requirement |
|--------|------------|
| **Availability** | High (relative to lab scale) |
| **Identity** | Stable and deterministic |
| **Network addressing** | Static via DHCP reservations |
| **Backup** | Mandatory |
| **Rebuild support** | Must assist rebuilds, not depend on them |

---

## 5. Provisioning Model

**Hypervisor Layer:**
- Proxmox installation performed via bootstrap process
- Post-install configuration via Ansible
- No Proxmox clustering required

**VM Lifecycle:**
- Management-plane VMs are created using **Ansible**
- Proxmox is treated as an API, not a declarative state engine
- Simplicity and traceability are prioritized

Terraform is intentionally **not used** for management-plane workloads.

---

## 6. Network Identity

All management-plane VMs:
- Use **deterministic MAC addresses**
- Receive **static DHCP mappings**
- Have predictable DNS records

Details are defined in the [MAC Namespace Specification](/docs/standards/mac-naming/).

---

## 7. Failure Philosophy

If something breaks:

- Tenant workloads may be destroyed and rebuilt
- Management-plane services must still be reachable
- Observability must continue to function
- Recovery tooling must remain online

If a service is required to **recover the platform**, it belongs on the management hypervisor.

---

## 8. Relationship to Other Documents

This document defines the **virtual management services architecture**.

Related documents:
- **[Management Plane](../management-plane/)** — Core Platform architecture (DNS authority, naming, provisioner role)
- **Correctness** — invariants that must always hold
- **Standards** — naming, DNS, and access rules derived from the management plane model
