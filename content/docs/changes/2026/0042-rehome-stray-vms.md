---
title: "CHG-0042: Two Undeclared VMs Moved Off the Management Hypervisor"
weight: -42
---

# CHG-0042: Two Undeclared VMs Moved Off the Management Hypervisor

| | |
|---|---|
| **Date** | 2026-11-20 |
| **Change type** | Migration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-21.** Both VMs kept as verified backups on the Builder, and removed from `dv02hyp001p01` |
| **Window** | 2026-11-20 to 2026-11-21. Each VM copied and its restore proven before anything was removed |
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

- [x] Where each VM goes is decided: kept as backups on the Builder, to restore later
- [x] Space for both backups off the host: the Builder's `/srv`

## Procedure

### Step 1: Look inside VM 100

Find anything the substrate still depends on, and move it into git or the vault.

**Done 2026-11-20, on the operator's word:** nothing on VM 100 is still needed.

### Step 2: Back up both

`vzdump` each VM, copy the archives off the host, and check each restores.

**Done 2026-11-20 and 2026-11-21.** Each VM, stopped, was backed up by `vzdump` (zstd), streamed
over SSH straight to the Builder's `/srv/pve1-vm-backups` at 100 MiB/s and the lowest disk
priority, with its sha256 recorded as it landed. Both hosts are on the management segment, so
nothing crossed the core router.

| VM | Read | Archive | Restore check |
|---|---|---|---|
| 100 `vdvntm-admin-01` | 64 GiB, 11 min | 18 GB | Restored to VMID 9100; its disk's sha256 matches the original's |
| 104 `vdvntm-winox` | 320 GiB, 56 min | 36 GB | Restored to VMID 9104; both disks and the TPM state match the original's |

Each check restored to `local-lvm-big-thin` under a spare VMID with its network removed, never
started, and was then deleted. VM 104 boots with SeaBIOS: its EFI disk was attached but unused,
and `vzdump` leaves such a disk out. The restored configuration still named the original's EFI
volume, so that line was removed from the test copy before it was deleted. The folder holds the
archives, their sha256s, each VM's configuration and a README with the steps to restore them on
another Proxmox node.

### Step 3: Bring them up at the destination

Restore at the destination and confirm each boots and works.

**Done 2026-11-21, as a kept archive.** The destination is the Builder's `/srv/pve1-vm-backups`,
to restore later, which the Goal allows. Step 2's restore checks are what prove it.

### Step 4: Remove them from the hypervisor

Delete both VMs and their disks from `dv02hyp001p01`, and update *Build a Hypervisor*.

**Done 2026-11-21.** `qm destroy 100 --purge` and `qm destroy 104 --purge`; no volume of either
is left, the service VMs ran throughout, and no VM disk is left on the data disk outside its thin pool.
*Build a Hypervisor* no longer lists them, and *VM Identity*'s sample report no longer shows VM 100.

## Verification

Both VMs run, or restore, at their destination; neither is on the management hypervisor.

## Undo

Until Step 4, nothing has changed on the hypervisor. After it, restore from the Step 2 archives.

## To discover

- **The destination, which is the operator's decision:** a tenant workload (tenant workloads are built
  from the template, so an existing disk needs importing), other hardware, or a kept archive to restore
  later.
- What VM 104 is used for, and whether it needs to run at all.

## To close

**What is left before this change closes, from its procedure and verification.**

- [x] Step 1: VM 100 checked for anything the substrate still depends on
- [x] Step 2: both VMs backed up, off the host, and each restore checked
- [x] Step 3: both brought up at their destination: kept as backups on the Builder
- [x] Step 4: both removed from `dv02hyp001p01`, and *Build a Hypervisor* updated
- [x] Verification: both restore from the Builder, and neither is on the management hypervisor
