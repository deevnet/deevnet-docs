---
title: "Virtual Services"
weight: 3
---

# Virtual Management Services

> **Scope**: This document covers services that run as **VMs on the management
> hypervisor**. For physical/hardware management services (DNS, DHCP, NAT),
> see the Core Router documentation
> ([OPNsense](/docs/platforms/opnsense-router/) or
> [VyOS](/docs/platforms/vyos-router/)).

## Purpose

The **management hypervisor** hosts infrastructure-critical services required to
**observe, automate, and access** the environment.

These services run as VMs to enable:
- Centralized logging and metrics collection
- Ansible execution environments
- Jump host access for recovery operations

If tenant workloads fail or are rebuilt, management services must remain available.

---

## Design Principles

Virtual management services follow a strict set of principles:

- **Stability over velocity**
- **Explicit configuration over convenience**
- **Recoverability over optimization**
- **Isolation from tenant experimentation**

The management hypervisor is intentionally boring. That is a feature.

---

## Platform Placement

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

## Core Responsibilities

### Observability
- Metrics collection (time-series data)
- Log aggregation
- Health dashboards
- Alerting and notifications

### Automation & Provisioning
- Ansible execution environments
- Image factory helpers
- Bootstrap coordination
- Inventory generation and validation

### Access & Recovery
- Jump hosts
- Out-of-band tooling
- Emergency access paths

---

## What Does NOT Run as VMs

The following services run on the **Core Router** (hardware layer), not as VMs:

| Service | Provider |
|---------|----------|
| DNS (authoritative and forwarding) | Core Router |
| DHCP (static mappings and dynamic pools) | Core Router |
| NAT/gateway | Core Router |
| Firewall rules | Core Router |

These services must remain operational even if all hypervisors are down.
See [Management Plane](management-plane/) for the physical vs virtual service distinction.

---

## Service Characteristics

| Attribute | Requirement |
|--------|------------|
| **Availability** | High (relative to lab scale) |
| **Identity** | Stable and deterministic |
| **Network addressing** | Static via DHCP reservations |
| **Backup** | Mandatory |
| **Rebuild support** | Must assist rebuilds, not depend on them |

---

## Provisioning Model

### Hypervisor Layer
- Proxmox installation performed via bootstrap process
- Post-install configuration via Ansible
- No Proxmox clustering required

### VM Lifecycle
- Management-plane VMs are created using **Ansible**
- Proxmox is treated as an API, not a declarative state engine
- Simplicity and traceability are prioritized

Terraform is intentionally **not used** for management-plane workloads.

---

## Network Identity

All management-plane VMs:
- Use **deterministic MAC addresses**
- Receive **static DHCP mappings**
- Have predictable DNS records

Details are defined in the
[MAC Namespace Specification](/docs/standards/mac-naming/).

---

## Failure Philosophy

If something breaks:

- Tenant workloads may be destroyed and rebuilt
- Management-plane services must still be reachable
- Observability must continue to function
- Recovery tooling must remain online

If a service is required to **recover the platform**, it belongs on the management hypervisor.

---

## Relationship to Other Docs

| Document | Relationship |
|---------|--------------|
| [Management Plane](management-plane/) | Defines physical vs virtual service boundaries |
| [Proxmox Hypervisors](/docs/platforms/proxmox-hypervisors/) | mgmt runs on dedicated hypervisor |
| [Bootstrap Node](/docs/platforms/bootstrap-node/) | Builds mgmt substrate |
| [MAC Namespace Specification](/docs/standards/mac-naming/) | Defines mgmt network identity |

---

## Summary

Virtual management services are the **observable and accessible layer** of Deevnet:

1. **Dedicated Proxmox hypervisor**
2. **Observability, automation, and access services only**
3. **Ansible-first lifecycle**
4. **Deterministic identity**
5. **Designed to survive tenant failure**

When everything else is broken, these services help recovery begin.
