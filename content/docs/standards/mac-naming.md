---
title: "MAC Namespace Specification"
weight: 5
---

# MAC Namespace Specification

## Purpose

This document defines the **deterministic MAC address strategy** used across the
Deevnet substrate, with a primary focus on **management-plane workloads**.

Deterministic MAC addressing enables:
- Stable DHCP reservations
- Predictable IP assignments
- Reproducible VM rebuilds
- Clear mapping between identity layers

> **Formatting**: All MAC addresses must follow the formatting rules in the
> [MAC Address Format Standard](../mac-address-format/) (lowercase hex, colon
> separators).

---

## Guiding Principles

- MAC addresses are **generated outside the hypervisor**
- MACs are **explicitly defined in inventory/code**
- Hypervisors must never auto-generate identity
- Identity must survive VM destruction and recreation

---

## Scope

| Workload Type | Policy |
|--------------|--------|
| **Management Plane** | Mandatory deterministic MACs |
| **Tenant Workloads** | Optional, future-controlled |
| **Ephemeral/Test VMs** | May use auto-generated MACs |

This specification applies **primarily to the management plane**.

---

## MAC Address Rules

### Locally Administered Addresses

All MAC addresses must:
- Use a **locally administered prefix**
- Avoid real vendor OUIs

The locally administered bit must be set.

Common valid first octets:
- `02`
- `06`
- `0A`
- `0E`

---

## Namespace Structure

The MAC namespace is structured to encode **environment and role intent**.

### Format

```

02:DD:EE:RR:NN:II

```


| Field | Meaning |
|-----|--------|
| `02` | Locally administered prefix |
| `DD` | Deevnet identifier |
| `EE` | Environment (dvnt / dvntm) |
| `RR` | Role identifier |
| `NN` | Node or service group |
| `II` | Instance index |

> Exact hex values are implementation-defined but must remain consistent.

---

## Example Assignments

| Hostname | MAC Address |
|--------|-------------|
| mgmt-dns-01 | 02:de:10:01:00:01 |
| mgmt-dhcp-01 | 02:de:10:02:00:01 |
| mgmt-metrics-01 | 02:de:10:03:00:01 |

These values are illustrative; the key requirement is **consistency**.

---

## Source of Truth

MAC addresses are stored in:
- Ansible inventory
- Variable files
- Version-controlled repositories

They are **never generated dynamically at runtime**.

Example inventory snippet:

```yaml
mgmt_dns_01:
  ansible_host: 192.168.10.10
  mac_address: "02:de:10:01:00:01"
```

---

## Related Standards

- [MAC Address Format](../mac-address-format/) - Formatting rules (lowercase, colons)
- [Management Hypervisor](/docs/platforms/management-plane/management-hypervisor/#deterministic-mac-addressing) -
  Platform implementation and policy rationale
