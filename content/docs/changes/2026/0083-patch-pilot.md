---
title: "CHG-0083: A First Patch Pass, Small and Careful"
weight: -83
---

# CHG-0083: A First Patch Pass, Small and Careful

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Upgrade |
| **Classification** | Routine |
| **Status** | **Planned** |
| **Window** | An evening, operator at the Builder. `dv02obj001v01` is down for its reboot, if it needs one: the tenant bucket store and Terraform state store do not answer for about a minute. `dv02bld002v01` serves no one. The hypervisors do not reboot |
| **Site** | mobile |
| **Systems** | `dv02obj001v01` (VMID 208), `dv02bld002v01` (VMID 203), `dv02hyp001p01`, `dv02hyp002p02` |
| **Automation** | None for the updates: `dnf` and `apt` on each host, by hand. Checked by the update watcher and `make discover` |
| **Risk** | Low. Most likely to go wrong: a VM's disk controller stalls under the install's writes ([INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/)), found by the VM not answering, and undone from its snapshot |
| **Related changes** | [CHG-0082](/docs/changes/2026/0082-update-watcher/), whose report lists what is waiting; [CHG-0080](/docs/changes/2026/0080-hyp002-proxmox-9-2-32/), whose throttled download this follows |
| **Related incidents** | [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/) (bulk transfers across the core router), [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) (an LSI controller's panic under disk load) |
| **Related runbooks** | [Patching](/docs/runbook/substrate/lifecycle/patching/) |

---

## Summary

**The update watcher's first report found about 1,700 updates waiting across the substrate, some
700 of them security updates, because nothing has applied updates since the hosts were built.** This
change is the first pass at them, chosen to prove a patch procedure where the risk is least, before
the hosts that carry tenants' services:

| Host | Waiting | Why it is in this pass |
|---|---|---|
| `dv02obj001v01` | 17, 8 of them security, `systemd` among them | The smallest set of any VM |
| `dv02bld002v01` | About 300 | The one service VM already on virtio-scsi, so not exposed to INC-0006's LSI panic. Its `dnf5` (5.4.1) is too old for the watcher's check, and this updates it |
| Both hypervisors | 5 each, all security: the Kerberos libraries (`libkrb5-3` and its companions) | A small download and no reboot |

Each VM is snapshotted first, downloads its updates at 1 MB/s while a watchdog proves the core
router still passes traffic, installs them, and reboots only if `dnf needs-restarting` says it must.
The other six service VMs are left for after their disk controllers move to virtio-scsi
([ADR-0046](/docs/architecture/decisions/substrate/0046-vm-hardware-profile/)); the Builder and `dv02bld001v01`, the control node, for
a change of their own.

**`dv02bld002v01` may be on its way out.** It was noted as a test builder to remove (2026-09-21). If
it still is, Step 3 can be dropped rather than patching a VM that will be deleted.

## Goal

- The update watcher reports `dv02obj001v01`, `dv02bld002v01` and both hypervisors with nothing
  waiting, and `dv02bld002v01` checked, no longer "could not check".
- Every service on `dv02obj001v01` answers as it did before.
- No ping missed across the core router while anything downloads.

## Scope

**In scope:** Fedora 44 updates on the two VMs, within the release; the five Kerberos packages on
each hypervisor.
**Out of scope:** the other six service VMs, the Builder, `dv02bld001v01`, the core router (on the
newest point release), the switch and AP, and Proxmox VE's own packages.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The download hangs the core router | `dv02cor002p01` | `--setopt=throttle=1M`, one host at a time, and a watchdog pinging `1.1.1.1` across the router throughout |
| The VM's disk controller stalls under the install | `dv02obj001v01` (emulated LSI) | Its set is the smallest; the operator watches it; a VM that stops answering is screendumped (`qm monitor 208`, `screendump`) before it is reset, then rolled back to its snapshot |
| An update breaks a service | `dv02obj001v01` | The snapshot. Rolling back also rolls back any bucket or state written since it was taken, so the window is short and the rollback decided at once |
| A hypervisor's services keep the old libraries in memory | both hypervisors | Nothing breaks: they load the new libraries at their next restart. No reboot is part of this change |

## Prerequisites

- [ ] The update watcher's latest report shows the counts above, or close to them
- [ ] Nothing else running on `dv02hyp001p01`'s data disk (no backup, no restore)
- [ ] The operator at the Builder, able to reach both hypervisors' consoles

## Procedure

### Step 1: Record where it starts

No outage.

**Run** (in `ansible-collection-deevnet.mgmt`): `make discover`. Keep `/srv/updates/latest.txt` as it
stands.

### Step 2: `dv02obj001v01`

1. **Snapshot**, on `dv02hyp001p01`: `qm snapshot 208 pre-chg-0083 --description "CHG-0083"`.
2. **Watchdog**, on the VM in a second session: `ping -i 2 1.1.1.1`.
3. **Download**, on the VM: `sudo dnf -y --setopt=throttle=1M upgrade --downloadonly`.
4. **Install:** `sudo dnf -y upgrade`.
5. **Reboot if needed:** `sudo dnf needs-restarting -r`; if it says a reboot is needed, `sudo reboot`.

**Verify:** the watchdog missed nothing during the download; `dnf check-upgrade` lists nothing; every
container unit on the VM is active (`systemctl --failed` is empty); the tenant bucket store and state
store answer through the service proxy, as they did in Step 1's report.

### Step 3: `dv02bld002v01`

As Step 2, with VMID 203. Its verification is the VM answering and `dnf check-upgrade` listing
nothing.

### Step 4: The hypervisors

One node at a time, `dv02hyp001p01` first. No outage.

**Run:**

```bash
apt-get install --only-upgrade krb5-locales libgssapi-krb5-2 libk5crypto3 libkrb5-3 libkrb5support0
```

**Verify:** `apt list --upgradable` no longer lists them; `pveversion` is unchanged; the node's web
interface answers.

### Step 5: The watcher and the catalog

**Run:** `make update-watch-now` (in `deevnet.builder`) and `make discover` (in `deevnet.mgmt`).

**Verify:** the report shows the four hosts with nothing waiting, `dv02bld002v01` checked. The
Software Catalog updated from the discovery report where a version it records changed.

### Step 6: Drop the snapshots

Three days later, if nothing has gone wrong: `qm delsnapshot 208 pre-chg-0083` and
`qm delsnapshot 203 pre-chg-0083`.

## Verification

The three points under Goal.

## Undo

**Steps 2 and 3:** `qm rollback <vmid> pre-chg-0083` on `dv02hyp001p01`, then start the VM. **Step 4**
is undone forward: a point update to a Debian security release is not reversed.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: discovery report taken
- [ ] Step 2: `dv02obj001v01` updated, its services answering, no ping missed
- [ ] Step 3: `dv02bld002v01` updated (or dropped, if it is being removed)
- [ ] Step 4: both hypervisors' Kerberos libraries updated
- [ ] Step 5: the watcher shows nothing waiting on the four hosts; the catalog updated
- [ ] Step 6: the snapshots dropped
- [ ] For an Upgrade: `make discover` (`deevnet.mgmt`) run after it, and the Software Catalog updated from its report

## Outcome

To be written when the change has run.

## Follow-ups

None yet.
