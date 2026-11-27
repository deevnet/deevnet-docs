---
title: "CHG-0100: The Tenant Workloads on the VM Hardware Profile"
weight: -100
---

# CHG-0100: The Tenant Workloads on the VM Hardware Profile

| | |
|---|---|
| **Date** | 2026-11-27 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-27** |
| **Window** | About 30 seconds' outage per workload, one at a time. The `cdeever`, `eds` and `tdemo` tenants agreed to the window on 2026-11-27 |
| **Site** | mobile |
| **Systems** | On `dv02hyp002p02`: `tdemo-backend` (2040), `eds-services` (2080), `cdeever-backend` (2160), `cdeever-oracle` (2161), `cdeever-postgres` (2162) |
| **Automation** | `qm set` by hand, as in CHG-0093; checked by `make vm-profile` (`deevnet.mgmt`) |
| **Risk** | Low. Most likely to go wrong: a workload does not find its root disk on the new controller and stops in the initramfs, undone by putting its saved configuration back |
| **Related changes** | [CHG-0093](/docs/changes/2026/0093-service-vms-virtio-scsi/), which moved the service VMs the same way; [CHG-0098](/docs/changes/2026/0098-vm-builders-apply-profile/), after which new workloads start on the profile |
| **Related incidents** | [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) (the LSI controller's panic) |

---

## Summary

**The five tenant workloads are the last VMs on the LSI controller INC-0006 panicked.** They were
cloned before the templates were on the profile, and the API never changes an adopted workload's
hardware. Each moves to `virtio-scsi-single`, with IO Thread, Discard and no cache on its disk, by a
shutdown, `qm set` and start. That is ADR-0046's last "every existing VM moved" item.

**The workloads are the tenants', so nothing runs inside them.** Each workload's state is read from
the hypervisor and its guest agent before and after: whether it runs, its OS and kernel, its
mounted filesystems and its addresses. The tenants' own services are theirs to check.

## Goal

`make vm-profile` reports only the declared exception; each workload runs as before.

## Prerequisites

- [x] The tenants agreed to the window
- [x] Each workload's configuration saved (`/root/chg-0100-<vmid>.conf` on `dv02hyp002p02`) and its
      state recorded (`/root/chg-0100-<vmid>.before`)

## Risk and impact

| Risk | Mitigation |
|---|---|
| A workload does not find its root disk and stops in the initramfs | Fedora's dracut includes the virtio drivers inside a VM; the seven service VMs moved this way (CHG-0093), and the tenant template boots on the profile (CHG-0098). `tdemo-backend` goes first, the others only after it passes. Undo: its saved configuration back |
| A workload boots a kernel its tenant installed but had not rebooted into | Not this change's doing, but recorded: the kernel after is compared with the kernel before |
| A tenant's service does not come back | The tenant checks it; the workload's own state is compared here |

## Procedure

### Step 1: Each workload, one at a time

**Run,** on `dv02hyp002p02`, in the order 2040, 2080, 2160, 2161, 2162:

```bash
qm shutdown <vmid> --timeout 180
qm set <vmid> --scsihw virtio-scsi-single \
  --scsi0 local-lvm:vm-<vmid>-disk-0,cache=none,discard=on,iothread=1,replicate=0,size=<size>
qm start <vmid>
```

**Verify:** the guest agent answers; the OS, mounts and addresses as before; the kernel as before or
newer.

**Undo:** `qm shutdown <vmid>`, then `qm set <vmid> --scsihw lsi --scsi0 <the saved scsi0>` and
`qm start <vmid>`.

### Step 2: The check

**Run:** `make vm-profile`; a reconcile of each tenant (`make reconcile NAME=<tenant>`).

**Verify:** 15 VMs, only the declared exception not compliant; each reconcile completes.

## Undo

Each workload separately, as in Step 1.

## To close

**This change closes when every item below is done.**

- [x] Step 1: all five on the profile and running as before
- [x] Step 2: `make vm-profile` reports only the declared exception; the reconciles completed

## Outcome

**Every VM on the site is on the profile, the standby builder's declared firmware exception
apart.** Each workload was down 24 to 25 seconds and came back with the same OS, kernel, mounts and
addresses. No tenant had a kernel pending.

| When (UTC) | Steps | What happened |
|---|---|---|
| Before 20:20 | Prerequisites | Configurations saved; state recorded. All five `lsi`, the agent answering, Fedora 44, `/` and `/boot` on XFS. Kernels: 2040 on 7.3.3, the others on 7.2.7 |
| 20:20:27–20:20:51 | 1 | `tdemo-backend` (2040): clean shutdown in 2 s, `qm set`, guest agent back 24 s after the shutdown began. State identical apart from the controller and disk options |
| 20:21:12–20:21:37 | 1 | `eds-services` (2080): the same, 25 s |
| 20:21:49–20:22:14 | 1 | `cdeever-backend` (2160): the same, 25 s |
| 20:22:26–20:22:51 | 1 | `cdeever-oracle` (2161): the same, 25 s |
| 20:23:03–20:23:28 | 1 | `cdeever-postgres` (2162): the same, 25 s |
| 20:23 | 2 | `make vm-profile`: 15 VMs, 14 compliant, 1 declared exception, 0 drift. `make reconcile` for `tdemo`, `eds` and `cdeever`: each reconciled |
| 20:24 | 2 | `make health-watch-now`: all well |

### Departures from the plan

None.
