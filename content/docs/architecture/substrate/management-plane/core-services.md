---
title: "Core Services"
weight: 2
---

# Core Services Architecture

### Purpose

This document defines the **foundational platform services** of the management plane—DNS, DHCP, NAT, routing, firewall, and the naming/authority model that underpins all substrate operations.

These services must remain operational even if all extended services are lost.

For the builder that provisions these services, see [Builder](../builder/).

---

## 1. Core Services

The Core Services provides foundational management services:

| Service | Description |
|---------|-------------|
| **DNS** | Authoritative for substrate zones, forwarding for external |
| **DHCP** | Static mappings for known hosts, dynamic pools |
| **NAT** | Outbound gateway for all segments |
| **Routing** | Inter-segment and gateway routing |
| **Firewall** | Inter-segment and egress rules |

In production, these services are provided by dedicated network infrastructure. The [Builder](../builder/) complements with provisioning, artifact hosting, and PXE/TFTP services.

---

## 2. Naming and DNS Model

### 2.1 Management Plane Zone

The management plane owns a dedicated DNS subdomain:

- `mgmt.deevnet.net`

This zone contains **management identities and services**, not workload endpoints.

---

### 2.2 Hosts vs Services

As with substrates, hosts and services are distinct.

- **Hosts** are replaceable implementations
- **Services** are stable contracts

Example host identity:
```
provisioner-01.mgmt.deevnet.net
```

Example service identities:
```
artifacts.mgmt.deevnet.net
pxe.mgmt.deevnet.net
tftp.mgmt.deevnet.net
console.mgmt.deevnet.net
```

Services may move between hosts without changing consumer configuration.

---

### 2.3 Authority

The management plane is authoritative for the `mgmt.deevnet.net` zone.

Substrate DNS zones:
- MUST NOT define management-plane records
- SHOULD delegate or forward `mgmt.deevnet.net` queries to the management plane

DNS authority boundaries are explicit and intentional.

---

## 3. DNS Operational Modes

The `mgmt.deevnet.net` zone operates in two modes depending on substrate state.

### 3.1 Production Mode

During normal operation:

- Dedicated network infrastructure is the DNS/DHCP authority for the substrate
- Management service records (artifacts, PXE, TFTP) resolve to the current provisioner host
- The builder's local DNS/DHCP services are **inactive**
- The builder uses a reserved IP outside the DHCP pool

### 3.2 Bootstrap Mode

During substrate build or recovery:

- The builder is the DNS/DHCP/TFTP authority
- The builder holds all `mgmt.deevnet.net` records locally
- Production network infrastructure may not exist yet
- The builder assumes the gateway IP for the management segment

### 3.3 No Runtime Conflict

Records are defined in both production network config and builder config, but:

- Only one authority is active at a time
- The builder's DNS/DHCP is disabled during production mode
- Production infrastructure does not exist (or is being rebuilt) during bootstrap mode

This is intentional duplication with exclusive activation, not conflicting truth.

For per-substrate implementation details, see [Core Services Implementation](/docs/platforms/management-plane/core-services/).
For the authority transition procedure, see [Authority Transition](/docs/runbook/authority-transition/).

---

## 4. Substrate Consumption of Management Services

Substrates expose **substrate-scoped service names** as their contract:

```
artifacts.dvnt.deevnet.net
artifacts.dvntm.deevnet.net
```

In management-authoritative mode, these may alias to management services:

```
artifacts.dvntm.deevnet.net
  -> artifacts.mgmt.deevnet.net
  -> provisioner-01-dvntm.mgmt.deevnet.net
```

Consumers never reference management-plane names directly.
