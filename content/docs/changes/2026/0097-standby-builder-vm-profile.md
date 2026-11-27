---
title: "CHG-0097: The Standby Builder on the VM Hardware Profile"
weight: -97
---

# CHG-0097: The Standby Builder on the VM Hardware Profile

| | |
|---|---|
| **Date** | 2026-11-27 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **In progress**: started 2026-11-27 |
| **Window** | A few minutes. The standby builder is shut down for the controller change and started again; nothing depends on it while it is idle, and the Builder is the control node throughout |
| **Site** | mobile |
| **Systems** | `dv02bld001v01` (VMID 202 on `dv02hyp001p01`) |
| **Automation** | `qm set` by hand, as in CHG-0093; checked by `make vm-profile` (`deevnet.mgmt`) |
| **Risk** | Low. Most likely to go wrong: the VM does not boot on the new controller, undone by putting the old configuration back |
| **Related changes** | [CHG-0093](/docs/changes/2026/0093-service-vms-virtio-scsi/), which moved the service VMs the same way; [CHG-0092](/docs/changes/2026/0092-builder-repave-f44/), whose follow-up this is |
| **Related incidents** | [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) (why the profile has IO Thread) |
| **Related runbooks** | [The Standby Builder](/docs/runbook/substrate/lifecycle/standby-builder/) |

---

## Summary

**The standby builder was kept on 2026-11-27 (CHG-0092), and `make vm-profile` reports it as
drift.** Its disk is on `virtio-scsi-pci` without IO Thread or Discard, and it boots OVMF on q35
where the profile has SeaBIOS on Proxmox's default machine.

**The disk moves to the profile; the firmware is declared an exception.** The builder kickstart lays
out a UEFI system only, so the VM must boot OVMF, the same reason `dv02bld002v01` has its exception
([ADR-0046](/docs/architecture/decisions/substrate/0046-vm-hardware-profile/) §2). Both controllers
use the guest's `virtio_scsi` driver, and the disks are found by UUID and by LVM, so the guest needs
no change.

## Goal

`make vm-profile` reports `dv02bld001v01` as compliant with a declared exception, and it runs as
before.

## Scope

**In scope:** the disk controller and the disk's options on VMID 202; its `vm_profile_exceptions` in
inventory.
**Out of scope:** the templates and the five tenant VMs on `dv02hyp002p02`, which `make vm-profile`
also reports as drift (still on LSI): ADR-0046's own remaining work.

## Risk and impact

| Risk | Mitigation |
|---|---|
| The VM does not boot on the new controller | Its configuration saved first; put back with `qm set`. The `pre-chg-0094` snapshot also holds the old configuration |
| A service on it does not come back | Its running services, listening ports and mounts compared before and after |

## Prerequisites

- [x] Nobody using the standby builder as a control node: the Builder is the control node

## Procedure

Every step runs from the Builder as `a_autoprov`, with `sudo` on `dv02hyp001p01`.

### Step 1: The exception in inventory

**Run:** a pull request adding `vm_profile_exceptions` (`bios: ovmf`, `machine: q35`, with the
reason) to `host_vars/dv02bld001v01/vars.yml`.

**Verify:** merged.

### Step 2: The controller and disk options

**Run:** save the VM's state and configuration, then:

```bash
qm config 202 > /root/chg-0097-202.conf
qm shutdown 202 --timeout 180
qm set 202 --scsihw virtio-scsi-single \
  --scsi0 local-lvm-big-thin:vm-202-disk-1,cache=none,discard=on,iothread=1,replicate=0
qm start 202
```

**Verify:** SSH answers; `systemctl is-system-running` is `running`; the services, listening ports and
mounts are as before; the guest agent answers (`qm agent 202 ping`).

**Undo:** `qm shutdown 202`, then `qm set 202 --scsihw virtio-scsi-pci --scsi0 local-lvm-big-thin:vm-202-disk-1`
and `qm start 202`.

### Step 3: The check

**Run:** `make vm-profile` (`deevnet.mgmt`).

**Verify:** `202 dv02bld001v01` compliant with its declared exception; the other VMs as before.

## Verification

The Goal: compliant with its exception, and its state the same as before.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: the exception merged
- [x] Step 2: the disk on the profile, the VM running as before
- [x] Step 3: `make vm-profile` reports it compliant with its exception

## Outcome

**The standby builder's disk is on the profile, and its firmware is a declared exception.** It was down
34 seconds and came back as it was.

| When | Steps | What happened |
|---|---|---|
| Before Step 2 | 3, before | `make vm-profile`: 15 VMs, 7 compliant, 8 drift; `202 dv02bld001v01`: `virtio-scsi-pci`, OVMF, q35, no IO Thread, Discard ignored |
| Before Step 2 | 1 | Pull request [ansible-inventory-deevnet #136](https://github.com/deevnet/ansible-inventory-deevnet/pull/136): `vm_profile_exceptions` (`bios: ovmf`, `machine: q35`) |
| 09:13:30–09:14:04 | 2 | Configuration saved (`/root/chg-0097-202.conf` on the hypervisor); clean shutdown in 5 s; `qm set` as planned; SSH back 24 s after start, 34 s down in all. `running`, no failed unit, `virtio_scsi` loaded, kernel 7.3.6; the disk now advertises discard (1 GiB). The guest agent answers. Services, listening ports and mounts identical to before |
| After Step 2 | 3 | `make vm-profile` (against #136's branch): `202 dv02bld001v01: EXCEPTION - UEFI network install from the builder kickstart`; 15 VMs, 7 compliant, 1 declared exception, 7 drift. The seven are the two templates and the five tenant VMs, still on LSI and out of scope |

### Departures from the plan

- **Step 3 ran before Step 1's pull request was merged**, against its branch checked out on the
  Builder. The change closes when it is merged.
