---
title: "CHG-0093: Service VMs Moved Off the LSI Disk Controller"
weight: -93
---

# CHG-0093: Service VMs Moved Off the LSI Disk Controller

| | |
|---|---|
| **Date** | 2026-11-26 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **In progress**: all seven VMs moved 2026-11-26; closes after the 17:00 backup, `make discover`, and the saved configurations removed |
| **Window** | One work session, operator at the Builder, one VM at a time. Each VM is shut down, reconfigured and started: down about two minutes. In turn: the log and metrics collector, the Omada controller (the APs and switch keep forwarding), the MQTT broker, the observability store, the bucket and state store, OpenBao and tenant DNS, then the Deevnet API, its database and the service proxy |
| **Site** | mobile |
| **Systems** | On `dv02hyp001p01`: `dv02col001v01` (VMID 206), `dv02nms001v01` (204), `dv02msg001v01` (205), `dv02obs001v01` (207), `dv02obj001v01` (208), `dv02idn001v01` (200), `dv02prv001v01` (201) |
| **Automation** | None: `qm` on `dv02hyp001p01`, by hand. Nothing in code sets a cloned VM's controller, so no play puts it back |
| **Risk** | Low. Most likely to go wrong: a VM does not find its root disk on the new controller and stops in the initramfs, undone by putting its saved configuration back |
| **Related changes** | [CHG-0083](/docs/changes/2026/0083-patch-pilot/), which left these VMs unpatched until this move and whose last open item (its snapshot) closes here; [CHG-0094](/docs/changes/2026/0094-patch-builder-service-vms/), the patch that follows |
| **Related incidents** | [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) (an LSI controller's panic under disk load), [INC-0002](/docs/incidents/2026/0002-controller-vm-network-hang/) (the same symptoms, unconfirmed), [INC-0007](/docs/incidents/2026/0007-api-sealed-after-power-on/) (the API after OpenBao restarts sealed) |
| **Related runbooks** | [Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/) |

---

## Summary

**All seven service VMs still have the emulated LSI 53C895A disk controller (`scsihw: lsi`) that
panicked under disk load in INC-0006.** [ADR-0046](/docs/architecture/decisions/substrate/0046-vm-hardware-profile/)
chose VirtIO SCSI single, with IO Thread, Discard and no host cache on every disk. CHG-0083 left six of these
VMs unpatched until they moved, because a patch's install is exactly the disk load that triggered the panic.
This change moves all seven in place, so CHG-0094 can patch them on the new controller.

**Every VM is ready to move in place,** as ADR-0046 §5 requires. Checked on 2026-11-26:

| Check | Result on all seven |
|---|---|
| `virtio_scsi` in the initramfs of the default kernel | present (Fedora's dracut adds the virtio drivers inside a VM) |
| Root on the kernel command line | by UUID |
| `/etc/fstab` | by UUID or label, no `/dev/sdX` |
| Firmware, NIC, CPU, guest agent | SeaBIOS, `virtio`, `host`, enabled: already ADR-0046's profile |

**Other disks are named by label or serial, not device.** `dv02obs001v01` and `dv02obj001v01` mount
their data disks by label (`deevnet-data`, and on `dv02obj001v01` also `dvnt-state` at `/srv/state`). `dv02prv001v01`'s
backup drive is a USB device passed through (`usb0`), which this change does not touch. The backup job
finds it by filesystem label.

**After this change the seven VMs match ADR-0046's profile.** The ADR's other work stays open: the
template, the builders and the compliance check.

## Goal

- `qm config` shows `scsihw: virtio-scsi-single` on all seven, and every `scsiN` disk with
  `iothread=1`, `discard=on` and `cache=none`.
- Every VM boots, its disks are mounted where they were, `systemctl --failed` is empty, and its service
  answers as before.
- The health watcher shows no new problem.
- `dv02obj001v01` has no `pre-chg-0083` snapshot, and CHG-0083 is closed.

## Scope

**In scope:** the disk controller and disk options of the seven service VMs on `dv02hyp001p01`.

**Out of scope:**
- The template (VMID 100), the builders and the compliance check: ADR-0046's other items.
- `dv02bld001v01`: already VirtIO SCSI, and to be destroyed under CHG-0092.
- The tenant workloads on `dv02hyp002p02`: they move only in windows their tenants agree to.
- Patching: CHG-0094.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The VM does not find its root disk and stops in the initramfs | any VM | Checked beforehand on all seven (above). The first VM moved is `dv02col001v01`, the least depended on, and the rest wait until it passes. Each VM's configuration is saved before it changes, so undo puts it back exactly |
| A data disk comes up under a different device name | `dv02obs001v01`, `dv02obj001v01` | They are mounted by label. Checked after boot: `findmnt /srv`, and `/srv/state` on `dv02obj001v01` |
| The backup runs while the API VM is down | `dv02prv001v01` | `deevnet-backup.timer` runs hourly. Move the VM right after a run finishes, once `systemctl is-active deevnet-backup.service` says `inactive` |
| OpenBao restarts sealed | `dv02idn001v01` | Expected ([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/)). Since CHG-0084 the egress list answers while it is sealed. Unseal it if the work session needs it |
| Discard starts returning blocks to the thin pool | every VM | Wanted. Fedora's weekly `fstrim.timer` does the trimming; the first run frees whatever has piled up, a burst of discards with no data written |
| A VM rebuilt from code comes back on LSI | any VM | Until the template is rebuilt (ADR-0046), a clone inherits `lsi`. Follow-up below |

## Prerequisites

- [ ] Nothing loading `dv02hyp001p01`'s data disk: no backup, no restore, no copy
- [ ] The operator at the Builder, able to reach `dv02hyp001p01`'s console
- [ ] `make health-watch-now` (in `deevnet.builder`): the starting state written down

## Procedure

Every `qm` command runs on `dv02hyp001p01` as root. `<vmid>` is the VM's VMID.

### Step 1: Close out CHG-0083

No outage.

**Run:** `qm delsnapshot 208 pre-chg-0083`.

**Verify:** `qm listsnapshot 208` shows only `current`. Then, in CHG-0083: tick its last
**To close** item, set its status to Complete, and add an Outcome row for the drop.

**Undo:** none. The snapshot is CHG-0083's from 2026-11-23, past its three days.

### Step 2: Move one VM, `dv02col001v01`

It is down for about two minutes. Logs and metrics wait in their senders' buffers and arrive after.

**Run:**

```bash
qm config 206 > /root/chg-0093-206.conf
qm shutdown 206 --timeout 180
qm set 206 --scsihw virtio-scsi-single \
  --scsi0 local-lvm-big-thin:vm-206-disk-0,cache=none,discard=on,iothread=1,replicate=0
qm start 206
```

**Verify:**

1. `qm config 206` shows `scsihw: virtio-scsi-single` and the `scsi0` options above.
2. The VM answers SSH. In it: `lsblk -o NAME,TRAN,MOUNTPOINT` shows `sda` on the new controller and
   mounted as before; `lsmod | grep virtio_scsi` lists the driver; `systemctl --failed` is empty.
3. Logs and metrics arrive in the observability store after the restart.

**Undo:** [Undo a VM](#undo-a-vm)

### Step 3: The other six, one at a time

As Step 2, in this order. The next VM starts only after the one before has passed its checks. Each
`scsiN` line is given again with its own options kept and the three profile options added:

| VM | VMID | Disks to set |
|---|---|---|
| `dv02nms001v01` | 204 | `--scsi0 local-lvm-big-thin:vm-204-disk-0,cache=none,discard=on,iothread=1,replicate=0` |
| `dv02msg001v01` | 205 | `--scsi0 local-lvm-big-thin:vm-205-disk-0,cache=none,discard=on,iothread=1,replicate=0` |
| `dv02obs001v01` | 207 | `--scsi0 local-lvm-big-thin:vm-207-disk-0,cache=none,discard=on,iothread=1,replicate=0` `--scsi1 local-lvm-big-thin:vm-207-disk-1,cache=none,discard=on,iothread=1,backup=0,serial=deevnet-data` |
| `dv02obj001v01` | 208 | `--scsi0 local-lvm-big-thin:vm-208-disk-0,cache=none,discard=on,iothread=1,replicate=0` `--scsi1 local-lvm-big-thin:vm-208-disk-1,cache=none,discard=on,iothread=1,backup=0,serial=deevnet-data` `--scsi2 local-lvm-big-thin:vm-208-disk-2,cache=none,discard=on,iothread=1,backup=0,serial=deevnet-state` |
| `dv02idn001v01` | 200 | `--scsi0 local-lvm-big-thin:vm-200-disk-0,cache=none,discard=on,iothread=1,replicate=0` |
| `dv02prv001v01` | 201 | `--scsi0 local-lvm-big-thin:vm-201-disk-0,cache=none,discard=on,iothread=1,replicate=0`, right after a backup run (above) |

Before each, compare the VM's `scsiN` lines in `qm config` with the table: a disk added since
2026-11-26 is set the same way, with its own options kept.

**Verify,** for each VM: Step 2's points 1 and 2, then its own service:

| VM | Check |
|---|---|
| `dv02nms001v01` | The Omada controller's web interface answers, and it shows the switch and AP connected |
| `dv02msg001v01` | The MQTT broker accepts a client again, and the log bridge's unit is active |
| `dv02obs001v01` | `findmnt /srv` shows the `deevnet-data` disk. The log and metrics stores and the dashboard answer through the service proxy |
| `dv02obj001v01` | `findmnt /srv` and `findmnt /srv/state` show their disks. `s3` and `tfstate` answer their health checks through the service proxy |
| `dv02idn001v01` | OpenBao answers its status, sealed. Tenant DNS answers a query for a tenant zone |
| `dv02prv001v01` | `make health-watch-now` shows "Deevnet API alive" and "Deevnet API database" ok. The egress agent on `dv02hyp002p02` succeeds on its next run. `blkid -t LABEL=<backup label>` finds the backup drive. The next hourly backup succeeds |

**Undo:** [Undo a VM](#undo-a-vm)

### Step 4: Check the whole

**Run:** `make health-watch-now` and `make update-watch-now` (in `deevnet.builder`).

**Verify:** no problem the starting state did not have; all seven VMs answer the update watcher.
On `dv02hyp001p01`, `qm config <vmid> | grep -E '^(scsihw|scsi[0-9])'` for each of the seven shows the
profile.

## Verification

The four points under Goal.

## Undo

### Undo a VM

The disks are not changed, only how they are attached. So undo puts the saved configuration's lines
back:

```bash
qm stop <vmid>
grep -E '^(scsihw|scsi[0-9]):' /root/chg-0093-<vmid>.conf    # the old lines
qm set <vmid> --scsihw lsi --scsi0 <the old scsi0 value> [--scsi1 … --scsi2 …]
qm start <vmid>
```

A VM stopped in the initramfs does not lose data: nothing was mounted read-write. Undo stays
practical for as long as the saved configurations are kept. Remove `/root/chg-0093-*.conf` when the
change closes.

## To close

**This change closes when every item below is done.**

- [x] Step 1: `pre-chg-0083` dropped, and CHG-0083 closed
- [x] Step 2: `dv02col001v01` moved, booted, its services as before
- [x] Step 3: the other six moved, each one's disks mounted and service answering
- [ ] Step 4: health and update watchers show no new problem; all seven on the profile
- [ ] The saved configurations removed from `dv02hyp001p01`

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| 15:57 | Prerequisites | `make health-watch-now`: all well. Nothing loading `dv02hyp001p01`'s disk (load 0.66). The API VM's hourly backup due at 16:00, so Step 2 waited for it |
| 15:57 | Step 1 | `qm delsnapshot 208 pre-chg-0083`: its three volumes removed in a second, `qm listsnapshot 208` shows only `current`. CHG-0083 closed |
| 16:00 | Prerequisites | The 16:00 backup finished, `Result=success` |
| 16:00:14–16:00:20 | Step 2 | `dv02col001v01`: configuration saved to `/root/chg-0093-206.conf`, shut down in 3 s, `scsihw: virtio-scsi-single` and `scsi0` with `discard=on,iothread=1` set, started |
| 16:00:41 | Step 2 | SSH up 21 s after start, booted 16:00:32 on kernel 7.2.5. `virtio_scsi` loaded, `sym53c8xx` not; `sda` with `/` and `/boot` mounted as before; discard on the disk; `systemctl is-system-running`: running, no failed unit; the same services as before. `make health-watch-now`: all well |
| 16:13:16–16:13:57 | Step 3 | `dv02nms001v01`: 41 s down, SSH 22 s after start. The controller's web interface 200 from the Builder at 16:14:39; every port it listened on before back by 16:16. One failed unit at boot, podman's first health check run while the controller started, which clears with the next check and appears on the two boots before this one too: not this change. `make health-watch-now` 16:16: all well |
| 16:16:38–16:17:07 | Step 3 | `dv02msg001v01`: 29 s down. Services, containers (`vernemq`, `vernemq-db`, `deevnet-log-bridge`), ports and mounts identical to before. A TLS handshake to 8883 from the Builder verifies the broker's certificate |
| 16:17:33–16:18:03 | Step 3 | `dv02obs001v01`: 30 s down. `/srv` on `deevnet-data` (`sdb`). Ten containers up; Grafana's port came up seconds after the first comparison, then every port as before. Through the proxy, with TLS verified: `grafana` `/api/health` 200, `logs` and `metrics` 401 (need a token), `ntfy` and `downloads` 200. `make health-watch-now` 16:18: all well |
| 16:18:47–16:19:15 | Step 3 | `dv02obj001v01`: 28 s down, all three disks moved. `/srv` on `deevnet-data`, `/srv/state` on `deevnet-state`. State identical; `s3`, `tfstate` and `tfstate:9000` health 200, as before |
| 16:19:54–16:20:20 | Step 3 | `dv02idn001v01`: 26 s down. State identical. Tenant DNS answers SOA for `tdemo`, `mabell`, `cdeever` and `129.20.10.in-addr.arpa` with the serials it had; OpenBao sealed and initialized, as before |
| 16:20:42–16:21:11 | Step 3 | `dv02prv001v01`: 29 s down, the backup inactive with the next run at 17:00. State identical; the backup drive found by label. `make health-watch-now` 16:21: "Deevnet API alive" and "Deevnet API database" ok. The egress agent's 16:23:32 run on `dv02hyp002p02`: success |
| 16:27 | Step 4 | `qm config`: all seven on `virtio-scsi-single`, every disk (11) with `iothread=1`, `discard=on`, `cache=none`. The update watcher reached all 11 hosts. `make discover` stopped at the core router for the vault password: left to the operator |

### Departures from the plan

- **`dv02col001v01` runs no collector.** Before the move it had only the base system's services,
  no containers, and nothing listening but SSH, so Step 2's check that logs and metrics arrive had
  nothing to check. It was checked by its services matching the ones before.
- **Step 3's per-VM state was compared by a script:** running services, containers, listening
  ports and mounts before the move against after, on top of each VM's own checks. It found nothing
  that stayed different.
- **No check that the Omada controller shows the switch and AP connected:** that needs the
  controller's credentials. `make discover` covers it, with the vault.
- **A kernel message, not new:** `virt/tdx: TDX not supported by the host platform` at boot. It is in
  `dv02nms001v01`'s boot log too, still on LSI: the kernel probing the host CPU, not this change.

## Follow-ups

- [ ] ADR-0046: rebuild the template on the profile, so a VM rebuilt from code does not come back on LSI
- [ ] ADR-0046: the tenant workloads on `dv02hyp002p02`, in windows their tenants agree to
