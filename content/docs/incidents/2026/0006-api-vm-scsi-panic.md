---
title: "INC-0006: The API VM's Kernel Panicked Under Backup Load"
weight: -6
---

# INC-0006: The API VM's Kernel Panicked Under Backup Load

| | |
|---|---|
| **Date** | 2026-11-20 |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (VMID 201 on `dv02hyp001p01`): the Deevnet API and its database. Seen by `dv02hyp002p02`'s egress agent |
| **Severity** | Low in effect. The API VM was dead for about 10 h 45 min, overnight. OpenBao was sealed throughout, as it is outside work sessions, so the API was already answering 503 before the crash and would have until a work session began. Tenant workloads kept their routes: the egress agent leaves them as they are when the API can't be reached |
| **Status** | Open · {{< inc-status "Mitigated" >}}. The VM was reset and came back whole. The preventive actions are open |
| **Times** | EST (UTC−5) |

---

## Summary

At about 23:05 on 2026-11-20, the guest kernel of `dv02prv001v01` panicked in its SCSI driver:

```
KERNEL PANIC!
assertion "i && sym_get_cam_status(cp->cmd) == DID_SOFT_ERROR" failed:
file "drivers/scsi/sym53c8xx_2/sym_hipd.c", line 3387
```

`sym53c8xx_2` drives the emulated LSI 53C895A controller (`scsihw: lsi`) the VM's disk hangs off.
The panic came while
[CHG-0042](/docs/changes/2026/0042-rehome-stray-vms/)'s backup work was loading the data disk the
VM's disk lives on. Proxmox went on reporting the VM as running. It was found the next morning,
during [CHG-0079](/docs/changes/2026/0079-proxmox-notifications/), from a failure line of the egress
agent's in `dv02hyp002p02`'s journal. A console capture named the cause before the reset.

## Impact

- **The Deevnet API and its database were down** from about 23:05 to 09:53, 10 h 48 min.
- **No request was refused that would otherwise have been served.** OpenBao was sealed from before
  the crash to after the recovery, so the API answered 503 to everything but `/healthz` on both
  sides of the outage.
- **Tenant egress was unaffected.** `dv02hyp002p02`'s egress agent, which renders tenant VRF
  default routes from the API every five minutes, failed each run and left the routes it had
  rendered before.

## Detection

Not by any monitor. While reading `dv02hyp002p02`'s mail log to confirm CHG-0079's test mail, a
line from the egress agent's failed unit appeared beside it. Its journal showed 503s until 23:04,
then connection timeouts from 23:09 on. The VM did not answer ping, its traffic counters did not
move, and its guest agent did not answer.

## Timeline

| Time (EST) | Event |
|---|---|
| 2026-11-20 19:56 | `dv02hyp001p01` boots with the mobile lab at its new location; the service VMs start |
| 20:04 (first logged) | The egress agent gets 503 from the API: OpenBao sealed, as outside work sessions |
| 22:18 | CHG-0042: `vzdump` of VM 104 starts, reading 320 GiB from `vgbigdata` at 100 MiB/s |
| 22:54 | CHG-0042: VM 100's test restore starts, writing 64 GiB into the `bigthin` pool on the same disk |
| 23:04 | Last 503 the egress agent logged |
| ~23:05 | **The guest kernel panics** in `sym53c8xx_2` |
| 23:06 | CHG-0042: the restore ends and the disk comparison starts, reading both 64 GiB disks |
| 23:09 | First connection timeout the egress agent logged |
| 23:14 | VM 104's backup ends |
| 2026-11-21 ~09:50 | Found from the egress agent's journal on `dv02hyp002p02` |
| 09:51 | Console captured: the panic above |
| 09:53 | `qm reset 201` |
| 09:54 | Back: SSH, the API and its database up, no failed units, `/healthz` 200; the API waits for OpenBao, which is sealed |

## Root cause

**The emulated LSI controller's guest driver panicked when disk requests stalled under heavy load
on the shared data disk.** The VM's disk is a thin volume in the `bigthin` pool on `vgbigdata`,
the same physical disk the CHG-0042 backup read from and the test restore wrote to. The
assertion is the driver's, on a command that came back with a soft error. A stall long enough
for a command to time out and be retried is the likeliest trigger. This is inferred from the
timing and the driver's message, not traced inside the guest.

**Seven other service VMs use the same controller** and did not panic; only
`dv02bld002v01` has `virtio-scsi-single`, the controller Proxmox recommends.

## Recovery

`qm reset 201`. The guest booted in about 30 seconds, with its database, API and service proxy
containers up and no failed units. The API logged "OpenBao is sealed or unreachable; waiting for
it": the state it was in before the crash.

## Contributing factors

- **The service VMs use an emulated LSI controller.** It is Proxmox's legacy default, and its
  guest driver is the one that panicked.
- **The backup and restore ran at 100 MiB/s on the disk the service VMs live on.** The limit was
  meant to spare those VMs and did not.
- **Nothing watches the API.** As in
  [INC-0002](/docs/incidents/2026/0002-controller-vm-network-hang/), a VM that Proxmox reports as
  running was dead, and nothing noticed overnight.

## Corrective actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Reset the VM, after capturing its console | `dv02prv001v01` | {{< action-status "Done" >}} 2026-11-21 |

## Preventive actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 2 | Give every VM one declared hardware profile, `virtio-scsi-single` with IO Thread among it, applied by every builder: [ADR-0046](/docs/architecture/decisions/substrate/0046-vm-hardware-profile/), then a change record to move the existing VMs | the template, `proxmox_vm`, the Deevnet API; every VM | {{< action-status "Open" >}} |
| 3 | Run large backups and restores on a hypervisor at a rate its service VMs can absorb, well under 100 MiB/s, or with the service VMs on another disk | the operator's procedure; *Build a Hypervisor* | {{< action-status "Open" >}} |
| 4 | Alert when the API stops answering, as INC-0002's action 3 asks for the controller | observability | {{< action-status "Open" >}} |

## Lessons learned

- **Capture first worked.** INC-0002's guest was rebooted before its console was read and was
  left without a cause. This time one screenshot named the driver. INC-0002 showed the same
  symptoms on a VM with the same controller; its cause is still not proven, but this is now the
  first thing to check.
- **A rate limit on the reader is not a limit on the disk.** 100 MiB/s of reads, alongside a
  restore's writes and a checksum's reads, was more than the service VMs' disk could share.

## Related changes

- [CHG-0042](/docs/changes/2026/0042-rehome-stray-vms/): the backup and restore that loaded the disk.
- [CHG-0079](/docs/changes/2026/0079-proxmox-notifications/): the work during which it was found.

## Related incidents

- [INC-0002](/docs/incidents/2026/0002-controller-vm-network-hang/): the same symptoms on
  `dv02nms001v01`, also on `scsihw: lsi`, with no console captured.
