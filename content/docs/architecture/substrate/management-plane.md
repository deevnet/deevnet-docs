---
title: "Management Plane"
weight: 2
---

# Deevnet Management Plane Architecture

### Purpose
This document defines the **Management Plane** within Deevnet.

The management plane is responsible for **provisioning, recovery, and out-of-band control** of substrates.
It exists *outside* normal workload substrates and may interact with multiple substrates simultaneously.

This document describes **architecture and intent**, not implementation details.

---

## 1. Architectural Role of the Management Plane

The management plane exists to answer one question:

> *How are substrates created, repaired, and controlled without depending on themselves?*

It provides:
- provisioning services (PXE, artifacts, bootstrap tooling),
- control-plane access (builders, bastions),
- and optional out-of-band services (serial consoles, OOB access).

It does **not** host tenant workloads.

---

## 1.1 Physical vs Virtual Management Services

The management plane encompasses both **physical** and **virtual** services:

### Physical Layer (Core Router)

Services that run on dedicated hardware (router/gateway appliance):

| Service | Description |
|---------|-------------|
| **DNS** | Authoritative for substrate zones, forwarding for external |
| **DHCP** | Static mappings for known hosts, dynamic pools |
| **NAT** | Outbound gateway for all segments |
| **Firewall** | Inter-segment and egress rules |

These services are provided by the Core Router ([OPNsense](/docs/platforms/opnsense-router/)
or [VyOS](/docs/platforms/vyos-router/)) and must remain operational even if all
hypervisors are down.

### Virtual Layer (Management Hypervisor)

Services that run as VMs on the dedicated management hypervisor:

| Service | Description |
|---------|-------------|
| **Observability** | Metrics collection, log aggregation, alerting |
| **Automation** | Ansible runners, image factory helpers |
| **Access** | Jump hosts, out-of-band tooling |

Virtual management services may be rebuilt from the physical layer.
See [Virtual Services](virtual-services/) for details on what runs on the management hypervisor.

---

## 2. Management Plane vs Substrates

### 2.1 Substrates
Substrates (e.g., `dvnt`, `dvntm`) represent **where workloads run**.

- each substrate has its own IP space
- each substrate has its own routing/security boundary
- each substrate may be independently provisioned, rebuilt, or torn down

Substrates are **consumers** of the management plane.

---

### 2.2 Management Plane
The management plane represents **how substrates are created and controlled**.

- it may have reachability into multiple substrates
- it may be multi-homed at the network level
- it is logically separate from all substrates

The management plane is **not a substrate**.

---

## 3. Naming and DNS Model

### 3.1 Management Plane Zone
The management plane owns a dedicated DNS subdomain:

- `mgmt.deevnet.net`

This zone contains **management identities and services**, not workload endpoints.

---

### 3.2 Hosts vs Services (Management Plane)
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

### 3.3 Authority
The management plane is authoritative for the `mgmt.deevnet.net` zone.

Substrate DNS zones:
- MUST NOT define management-plane records
- SHOULD delegate or forward `mgmt.deevnet.net` queries to the management plane

DNS authority boundaries are explicit and intentional.

---

## 4. DNS Operational Modes

The `mgmt.deevnet.net` zone operates in two modes depending on substrate state.

### 4.1 Router-Authoritative (BAU)

During normal operation:

- Core Router is the DNS authority for the substrate
- Core Router holds `mgmt.deevnet.net` records (CNAMEs → provisioner host A record)
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

### 4.2 Provisioner-Authoritative (Rebuild)

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

### 4.3 No Runtime Conflict

Records exist in both Core Router config and provisioner dnsmasq config, but:

- only one authority is active at a time
- provisioner's dnsmasq is disabled during BAU
- Core Router does not exist (or is being rebuilt) during provisioner-authoritative mode

This is intentional duplication, not conflicting truth.

---

## 5. Replaceable Provisioner Role

### 5.1 Provisioner Is a Role, Not a Pet
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

### 5.2 Multi-Homing Without Identity Confusion
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

## 6. Substrate Consumption of Management Services

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

---

## 8. Architectural Invariants

The management plane architecture is considered **correct** when:

- substrates can be provisioned without depending on themselves
- management services have stable DNS identities
- provisioner hosts are replaceable without consumer impact
- multi-homed reachability is explicit in naming
- substrates remain authoritative only for substrate concerns

If a substrate must be "mostly working" in order to be rebuilt, the architecture is incorrect.

---

## 9. Relationship to Other Documents

This document defines **what exists**.

Related documents define:
- **Correctness** — invariants that must always hold
- **Secure Identity** — how access and secrets are handled
- **Provisioning Architecture** — how management services are used during bootstrap
- **Standards** — naming, DNS, and access rules derived from this model
