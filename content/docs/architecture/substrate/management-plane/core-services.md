---
title: "Core Services"
weight: 1
---

# Core Services Architecture

### Purpose

This document defines the **physical core services** of the management plane—the Core Router and Bootstrap Node that form the foundational tier of substrate infrastructure.

These services must remain operational even if all virtual infrastructure is lost.

---

## 1. Core Platform

The Core Platform is dedicated hardware providing foundational management services:

| Service | Description |
|---------|-------------|
| **DNS** | Authoritative for substrate zones, forwarding for external |
| **DHCP** | Static mappings for known hosts, dynamic pools |
| **NAT** | Outbound gateway for all segments |
| **Firewall** | Inter-segment and egress rules |

These services are provided by the Core Router. The Bootstrap Node complements the Core Router with provisioning, artifact hosting, and PXE/TFTP services. Together they form the Core Platform.

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

### 3.1 Router-Authoritative (BAU)

During normal operation:

- Core Router is the DNS authority for the substrate
- Core Router holds `mgmt.deevnet.net` records (CNAMEs -> provisioner host A record)
- Provisioner's dnsmasq is **disabled**
- Provisioner uses reserved IP at low end of subnet (e.g., `192.168.10.95`)

Example records in Core Router:
```
provisioner-01.mgmt.deevnet.net  A     192.168.10.95
artifacts.mgmt.deevnet.net       CNAME provisioner-01.mgmt.deevnet.net
pxe.mgmt.deevnet.net             CNAME provisioner-01.mgmt.deevnet.net
tftp.mgmt.deevnet.net            CNAME provisioner-01.mgmt.deevnet.net
```

---

### 3.2 Provisioner-Authoritative (Rebuild)

During substrate rebuild:

- Provisioner is the DNS/DHCP/TFTP authority
- Provisioner's dnsmasq holds `mgmt.deevnet.net` records
- Core Router may not exist (or may be the host being provisioned)
- Provisioner uses gateway IP (e.g., `192.168.10.1`)

Example records in provisioner dnsmasq:
```
provisioner-01.mgmt.deevnet.net  A     192.168.10.1
artifacts.mgmt.deevnet.net       CNAME provisioner-01.mgmt.deevnet.net
pxe.mgmt.deevnet.net             CNAME provisioner-01.mgmt.deevnet.net
tftp.mgmt.deevnet.net            CNAME provisioner-01.mgmt.deevnet.net
```

---

### 3.3 No Runtime Conflict

Records exist in both Core Router config and provisioner dnsmasq config, but:

- only one authority is active at a time
- provisioner's dnsmasq is disabled during BAU
- Core Router does not exist (or is being rebuilt) during provisioner-authoritative mode

This is intentional duplication, not conflicting truth.

---

## 4. Replaceable Provisioner Role

### 4.1 Provisioner Is a Role, Not a Pet

The provisioner is a **role** that any suitable host can assume via code.

- no host is permanently "the provisioner"
- rebuilding or replacing the provisioner is expected
- authority is logical, not physical

Example:
```
artifacts.mgmt.deevnet.net -> provisioner-01.mgmt.deevnet.net
```

Switching provisioners requires only DNS changes, not consumer changes.

---

### 4.2 Multi-Homing Without Identity Confusion

A management host may be reachable from multiple substrates.

Instead of ambiguous multi-A records, **interface-specific identities** may be published:

```
provisioner-01-dvnt.mgmt.deevnet.net
provisioner-01-dvntm.mgmt.deevnet.net
```

Each name maps to the IP address used by that substrate.

This preserves:
- truthful routing
- clear firewall policy
- explicit blast-radius boundaries

---

## 5. Substrate Consumption of Management Services

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

---

## 6. Builder (Bootstrap Node)

The **builder** is the architectural role responsible for provisioning and configuring all substrate infrastructure. This role is implemented by the bootstrap node.

Every substrate needs a way to be created from scratch:

> *How do you provision infrastructure when no infrastructure exists yet?*

The builder answers this by providing:
- A self-contained provisioning platform
- All artifacts needed for air-gapped deployment
- Automation to configure every substrate component
- Authority transition from bootstrap to production

### Key Properties

**Self-Contained** — Contains everything needed to stand up a substrate:
- Automation code (Ansible collections, playbooks)
- Artifact server (OS images, packages, kickstarts)
- Network boot infrastructure (TFTP, GRUB configs)
- Git repositories for all IaC

**Portable** — A single builder can move between substrates:
- Same physical device serves dvntm or dvnt
- Provisions whichever environment it's connected to
- No substrate-specific hardware requirements

**Air-Gapped Capable** — Once artifacts are staged, the builder can provision without upstream internet:
- All required images stored locally
- No external dependencies during provisioning
- Critical for isolated or bandwidth-limited deployments

**Disposable Authority** — The builder has temporary authority during bootstrap:
- May serve as DNS/DHCP/gateway initially
- Hands off control to Core Router once configured
- Becomes a regular admin host in production

### Authority Transition

The builder participates in explicit authority transitions:

| Phase | Builder Role | Core Router Role |
|-------|-------------|------------------|
| **Bootstrap** | DNS, DHCP, gateway, TFTP, artifacts | Does not exist |
| **Transition** | TFTP, artifacts | DNS, DHCP, gateway |
| **Production** | TFTP, artifacts, Ansible controller | DNS, DHCP, gateway, firewall |

The transition is explicit and deliberate—never automatic.

### Relationship to Tenants

The builder provisions **substrate infrastructure only**:
- Core Router configuration
- Hypervisor setup
- Management plane VMs
- Network switch and AP configuration

Tenant workloads use a different provisioning model. See
[Tenant Building](/docs/architecture/tenant/building/) for tenant-specific
provisioning architecture.

### Implementation

The builder role is implemented by the **bootstrap node**:

| Aspect | Implementation |
|--------|----------------|
| **Hardware** | Mini PC with dual NICs |
| **OS** | Fedora with `deevnet.builder` collection |
| **Artifacts** | nginx serving images and packages |
| **Network boot** | in.tftpd with GRUB configs |
| **Automation** | Ansible controller for all substrate hosts |

See [Bootstrap Node](/docs/platforms/management-plane/bootstrap-node/) for implementation details.

### Design Principles

**Ansible-First** — All substrate provisioning uses Ansible: idempotent configuration, version-controlled playbooks, traceable changes, no Terraform for substrate infrastructure.

**Deterministic Identity** — All provisioned hosts receive: deterministic MAC addresses (for VMs), static DHCP reservations, predictable DNS records, inventory-defined identity.

**Explicit Authority** — Authority transitions are: documented in runbooks, triggered manually, validated before completion, never automatic.

---

## 7. Out-of-Band and Adjacent Services

The management plane is the natural home for OOB and control infrastructure, including:

- serial console servers
- OOB management gateways
- bastion or jump hosts
- emergency recovery tooling

These services:
- live in `mgmt.deevnet.net`
- are independent of any substrate lifecycle
- remain reachable even when substrates are impaired
