---
title: "Hypervisor Storage"
weight: 7
tasks_completed: 0
tasks_in_progress: 1
tasks_planned: 5
---

# Hypervisor Storage

Give each hypervisor a deliberate, documented storage layout, and make the storage a rebuild
depends on recoverable from code.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

The hypervisors' storage grew by hand. Nothing records why each node is laid out the way it is, and
until recently nothing recorded the layout at all. This project first captures what exists, so a
rebuild recreates it, and then improves it.

**In Scope**
- Recording each node's data-disk storage in inventory, and recreating it from there
- A storage standard for hypervisors: which disk holds what, pool naming, thin versus thick
- Bringing `dv02hyp001p01` and `dv02hyp002p02` in line with that standard
- What happens to guest disks, and guest configuration, when a node's OS disk is rebuilt

**Out of Scope**
- Shared storage across nodes, which is still a planned addition to
  [Substrate Storage](/docs/architecture/substrate/storage/)
- The VM disk model (OS disk versus data disk), which that page already defines

---

## Current layout of dv02hyp001p01

Read on the node on 2026-09-14 with `lsblk`, `vgs` and `lvs`.

| Disk | Size | Volume group | Contents |
|---|---|---|---|
| OS disk | 476.9G | `pve` (installer) | root 96G, swap 8G, thin pool `data` 348.8G (`local-lvm`), 16G free. Holds VM 100's disk. |
| Data disk | 1.8T, one partition | `vgbigdata` | thin pool `bigthin` 1.07T (`local-lvm-big-thin`): the Fedora template and the provisioner VMs. Thick LVs for VM 104 (`local-lvm-big`, an `lvm` storage on the same volume group). 442.86G free. |

Things this layout does not explain:
- **Two thin pools.** The installer's `local-lvm` on the OS disk is nearly unused, while management
  VMs go to the data disk.
- **Mixed provisioning.** VM 104 uses thick volumes directly in `vgbigdata` (storage
  `local-lvm-big`), beside a thin pool in the same volume group.
- **The name.** `local-lvm-big-thin` suggests the installer's local storage, but it lives on
  another disk.
- **Different pools per node.** `dv02hyp002p02` uses `local-lvm`, so the image factory needs a
  per-node storage override.
- **No redundancy.** Each data disk is a single disk. Losing it loses every VM disk on it.

---

## Record the layout as code 🔄

- 🔄 Declare `dv02hyp001p01`'s data-disk volume group, thin pool and PVE storage entries in inventory,
  applied by `deevnet.builder`'s `proxmox_node_storage` role. A reinstalled OS disk gets its
  storage entries back; a replacement data disk gets its volume group and pool recreated.

## Decide the standard ⏳

- ⏳ Write a hypervisor storage standard: the OS disk holds the OS only (or also guests); where
  templates, management VMs and data disks live; thin versus thick; how pools and storage IDs
  are named
- ⏳ Decide what a data-disk failure should cost, and whether that calls for redundancy or for
  backups

## Converge the nodes ⏳

- ⏳ Bring `dv02hyp001p01` to the standard: retire or repurpose the unused `local-lvm`, move VM 104
  off thick volumes or document why it stays, and rename storage where it is worth the migration
- ⏳ Apply the same standard to `dv02hyp002p02`, and drop the image factory's per-node storage
  override if the pools converge

## Guest configuration survives a rebuild ⏳

- ⏳ Guest definitions live in `/etc/pve` on the OS disk, so a reinstall loses them even when their
  disks survive on the data disk. Back them up, or rely on rebuilding every guest from code, and
  say which in the recovery runbook.
