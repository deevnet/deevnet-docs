---
title: "MAC Namespace Specification"
weight: 6
---

# MAC Namespace Specification

## Purpose

This document defines the **deterministic MAC address strategy** used across the
Deevnet platform, with a primary focus on **management-plane workloads**.

Deterministic MAC addressing enables:
- Stable DHCP reservations
- Predictable IP assignments
- Reproducible VM rebuilds
- Clear mapping between identity layers

> **Formatting**: All MAC addresses must follow the formatting rules in the
> [MAC Address Format Standard](/docs/standards/mac-address-format/) (lowercase hex, colon
> separators).

---

## Guiding Principles

- MAC addresses are **generated outside the hypervisor**
- MACs are **explicitly defined in inventory/code**
- Hypervisors must never auto-generate identity
- Identity must survive VM destruction and recreation

---

## Scope

Two rules, not one. The distinction is which side of the boundary the NIC was
created on.

| Class | Policy |
|-------|--------|
| **Assigned** — any NIC we create (management-plane VMs) | **Derived** from this namespace, never invented |
| **Observed** — bare-metal NICs, and guests that predate this scheme | Recorded **as found**, real vendor OUIs and all |

An observed MAC is a fact about hardware. Rewriting one means a NIC change plus
a DHCP change, so they are left alone and simply documented. Both classes live at
`infrastructure.interfaces.<iface>.mac` and are authoritative in git.

The workload policy is unchanged:

| Workload Type | Policy |
|--------------|--------|
| **Management Plane** | Mandatory deterministic MACs |
| **Tenant Workloads** | Optional, future-controlled |
| **Ephemeral/Test VMs** | May use auto-generated MACs |

---

## MAC Address Rules

### Locally Administered Addresses

All **assigned** MAC addresses must:
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

The namespace is a fixed three-octet prefix plus a three-octet suffix whose
**encoding is defined per class of host**.

```
02:DD:EE : <--- 3-octet suffix, encoding defined per host class --->
```

| Field | Meaning |
|-----|--------|
| `02` | Locally administered prefix |
| `DD` | Deevnet identifier (`de`) |
| `EE` | Environment — the site octet of [ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/): `20` = dvntm, `10` = dvnt |

The environment octet is **derived from the addressing plan**, not restated, so
the namespace follows the environment with no second place to edit. Because it
is part of the prefix, two substrates cannot collide even when they reuse the
same suffix.

### Management-plane VMs: the suffix is the VMID

For management-plane VMs the suffix is the **Proxmox VMID, big-endian across
three octets**:

```
02:de:<site octet>:(vmid >> 16):(vmid >> 8 & 0xff):(vmid & 0xff)
```

An earlier draft of this standard encoded role, node group and instance index
into those three octets. That was dropped: role encoding requires a
hand-maintained registry mapping roles to numbers, which is precisely the
error-prone artefact deterministic addressing is meant to remove. The VMID is a
registry that already exists, that the hypervisor already enforces uniqueness
on, and that a management VM must declare anyway.

The consequence is that **adding a management VM is "allocate a VMID"** —
everything else follows from it.

Three octets bound the VMID at **16777215**, well beyond any realistic value.

> **The VMID is identity, not sizing.** Changing it changes the MAC, and
> therefore the DHCP reservation and the address. It is a renumbering, not a
> resize.

---

## Uniqueness

VMID uniqueness must hold **across the whole substrate**, not per node. The
management and tenant hypervisors are deliberately
[not clustered](/docs/platforms/management-plane/management-hypervisor/), so
Proxmox enforces uniqueness only within a single node — nothing at the
hypervisor layer prevents the same VMID existing twice.

Two VMs sharing a VMID would share a MAC, and the DHCP reservation for it would
flip between their two addresses on every run. Substrate-wide uniqueness is
therefore enforced by the allocator described in
[Allocate VM Identity](/docs/runbook/building-recovery/vm-identity/), which
surveys every hypervisor before answering and refuses to allocate from a partial
survey.

---

## Example Assignments

| Hostname | VMID | MAC Address |
|--------|------|-------------|
| tenant-mgmt-vm01 (dvntm) | 200 | `02:de:20:00:00:c8` |
| — the same VMID in dvnt | 200 | `02:de:10:00:00:c8` |
| — VMID 201 in dvntm | 201 | `02:de:20:00:00:c9` |

---

## Source of Truth

MAC addresses are stored in:
- Inventory
- Variable files
- Version-controlled repositories

They are **never discovered at runtime**. Nothing may read a MAC off a
hypervisor during a play and act on it: that would make the DHCP configuration a
function of live hypervisor state rather than of the repository, and a rebuild
would silently renumber the host.

**Deterministic derivation is not runtime discovery.** An assigned MAC is
computed once, from a VMID that is itself declared, and written into
version-controlled inventory as a literal. The function is pure — same VMID,
same MAC, on every run, from any control node, with the hypervisor uninvolved —
and the result is reviewable in a diff. That is what the allocator does, and it
satisfies this rule rather than bending it.

Example inventory layout. The hand-written file references the generated one, so
an operator's prose and a machine's output never contend for the same file:

```yaml
# host_vars/tenant-mgmt-vm01/vars.yml   (hand-written)
infrastructure:
  form: vm
  interfaces:
    eth0:
      mac: "{{ deevnet_assigned_mac | default('') }}"

mgmt_vm:
  vmid: "{{ deevnet_assigned_vmid | default(0) }}"
```

```yaml
# host_vars/tenant-mgmt-vm01/identity.yml   (GENERATED - do not edit)
deevnet_assigned_vmid: 200
deevnet_assigned_mac: "02:de:20:00:00:c8"
```

Observed MACs are written as plain literals in the same `infrastructure` block,
with no generated file.

---

## Related Standards

- [MAC Address Format](/docs/standards/mac-address-format/) - Formatting rules (lowercase, colons)
- [Extended Services](/docs/architecture/substrate/management-plane/extended-services/) -
  Extended management services architecture and network identity
