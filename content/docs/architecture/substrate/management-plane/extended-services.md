---
title: "Extended Services"
weight: 3
---

# Extended Services Architecture

### Purpose

This document defines the **extended management services** layer within the Deevnet management plane.

Extended management services provide observability, automation, and access tooling. They are **additive** to [Core Services](/docs/architecture/substrate/management-plane/core-services/)—the minimal set of services required for the substrate to function on its own.

These services may be rebuilt entirely from the builder and core services. If the extended services tier is lost, core provisioning and network services remain operational.

For core management plane architecture (DNS authority, naming, provisioner role, OOB services), see [Core Services](/docs/architecture/substrate/management-plane/core-services/).

---

## 1. Service Overview

Services that run in the extended management tier:

| Service | Description |
|---------|-------------|
| **Observability** | Metrics collection, log aggregation, alerting |
| **Automation** | Build automation runners, image factory helpers |
| **Access** | Jump hosts, out-of-band tooling |
| **Tenant authoritative DNS** | PowerDNS holding per-tenant delegated zones ([ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/)) |

### 1.1 Two Service Hosts, Split by Audience

Extended services are grouped onto shared hosts rather than one host per service, and the grouping
follows **who the service serves**:

| Host | Serves | Examples |
|------|--------|----------|
| **Tenant-facing** | Substrate services that tenants consume | Tenant authoritative DNS |
| **Substrate-facing** | Services the substrate consumes about itself | Observability, automation, access |

Both are substrate-owned. Naming a host for its audience follows the same convention as the
`tenant_transit` and `tenant_underlay` VLANs of
[ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/) — substrate resources named
for the tenants they carry.

The split exists for **change cadence**. Observability is poked at constantly; tenant DNS should be
boring. Keeping them on separate hosts means a restart or an update in the noisy tier cannot take
tenant name resolution with it. Service endpoints are CNAMEs, so a service may move between hosts
without changing what consumers reference.

---

## 2. Isolation Model

Extended management services are isolated from tenant workloads.

| Attribute | Value |
|---------|------|
| **Workload type** | Infrastructure-critical |
| **Change cadence** | Slow and deliberate |
| **Blast radius** | Isolated from tenants |

This separation ensures:
- Tenant rebuilds cannot disrupt core services
- Observability and access remain available during failures
- Platform recovery paths are always reachable

Isolation here means **no tenant code runs in this tier**. A service may still *serve* tenants —
tenant authoritative DNS does — without a tenant being able to execute in it or write outside its
own namespace.

---

## 3. Design Principles

Extended management services follow a strict set of principles:

- **Stability over velocity**
- **Explicit configuration over convenience**
- **Recoverability over optimization**
- **Isolation from tenant experimentation**

The extended services tier is intentionally boring. That is a feature.

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

Extended services are provisioned from the builder:

- Post-install configuration via build automation
- Management-plane VMs are created using build automation tooling
- Simplicity and traceability are prioritized

Terraform is intentionally **not used** for management-plane workloads.

This holds even where a service exists to serve tenants. Under
[ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/) the DNS **server** is
substrate and is provisioned by Ansible; the **records** inside its zones are tenant content and
are written by the tenant's own Terraform. Substrate provides the machine, tenants provide the
content — so no Terraform state is introduced for the substrate.

For the current platform and tooling used to host extended services,
see [Implementation & Tooling](/docs/platforms/).

---

## 6. Network Identity

All management-plane hosts:
- Have **stable, predictable network identities**
- Receive **static address assignments**
- Have deterministic DNS records

---

## 7. Failure Philosophy

If something breaks:

- Tenant workloads may be destroyed and rebuilt
- Management-plane services must still be reachable
- Observability must continue to function
- Recovery tooling must remain online

If a service is required to **recover the platform**, it belongs in the extended services tier.
