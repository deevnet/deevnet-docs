---
title: "CHG-0042: Two Undeclared VMs Moved Off the Management Hypervisor"
weight: -42
---

# CHG-0042: Two Undeclared VMs Moved Off the Management Hypervisor

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Migration |
| **Classification** | Routine |
| **Status** | Planned |
| **Window** | Unscheduled. Each VM is copied before anything is removed |
| **Site** | mobile |
| **Systems** | `dv02hyp001p01`: VM 100 `vdvntm-admin-01` and VM 104 `vdvntm-winox` |
| **Automation** | Proxmox's own backup and restore (`vzdump`, `qmrestore`), run by hand; the destination's own tooling |
| **Risk** | Low. Most likely to go wrong: removing a VM before its copy is proven to start. Nothing is removed until it is |
| **Related changes** | None |
| **Related incidents** | None |
| **Related runbooks** | [Build a Hypervisor](/docs/runbook/substrate/building-recovery/build-hypervisor/) |

---

## Summary

Two VMs on the management hypervisor are not in inventory, so no rebuild recreates them. They are kept,
not deleted, but the substrate hypervisors run the lab now: anything that isn't the substrate lives in
a tenant or on other hardware
([2026-10 review: R9](/docs/architecture/reviews/2026-10-rebuild-and-access/#r9-the-manual-floor)).
VM 100 is where the automation key was made, so it is examined before it moves.

## Goal

- Both VMs run somewhere other than the substrate hypervisors, or are kept as verified backups to run
  later.
- Neither is on `dv02hyp001p01`.
- *Build a Hypervisor* no longer lists them.

## Scope

**In scope:** the two VMs.
**Out of scope:** what runs inside them.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Losing a VM's contents | `dv02hyp001p01` | A full backup of each, copied off the host and restored once, before removal |
| Something on VM 100 the site still needs | VM 100 | Look before moving: keys, scripts, anything the substrate still uses moves into the repositories or the vault first |

## Prerequisites

- [ ] Where each VM goes is decided (below)
- [ ] Space for both backups off the host

## Procedure

### Step 1: Look inside VM 100

Find anything the substrate still depends on, and move it into git or the vault.

### Step 2: Back up both

`vzdump` each VM, copy the archives off the host, and check each restores.

### Step 3: Bring them up at the destination

Restore at the destination and confirm each boots and works.

### Step 4: Remove them from the hypervisor

Delete both VMs and their disks from `dv02hyp001p01`, and update *Build a Hypervisor*.

## Verification

Both VMs run, or restore, at their destination; neither is on the management hypervisor.

## Undo

Until Step 4, nothing has changed on the hypervisor. After it, restore from the Step 2 archives.

## To discover

- **The destination, which is the operator's decision:** a tenant workload (tenant workloads are built
  from the template, so an existing disk needs importing), other hardware, or a kept archive to restore
  later.
- What VM 104 is used for, and whether it needs to run at all.
