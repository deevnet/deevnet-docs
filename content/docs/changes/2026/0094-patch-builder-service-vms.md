---
title: "CHG-0094: The Builder and Six Service VMs Patched Within Fedora 44"
weight: -94
---

# CHG-0094: The Builder and Six Service VMs Patched Within Fedora 44

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Upgrade |
| **Classification** | Routine |
| **Status** | Planned |
| **Window** | One work session, operator at the Builder, one host at a time. Each host is down for its reboot, about a minute. In turn: the Omada controller (the APs and switch keep forwarding), the log and metrics path, the MQTT broker, OpenBao and tenant DNS, then the Deevnet API, its database and the service proxy. Each VM's download at 1 MB/s takes several minutes |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the Builder); on `dv02hyp001p01`: `dv02nms001v01` (VMID 204), `dv02col001v01` (206), `dv02msg001v01` (205), `dv02obs001v01` (207), `dv02idn001v01` (200), `dv02prv001v01` (201) |
| **Automation** | None for the updates: `dnf` on each host, by hand, as in CHG-0083. Checked by the update and health watchers (`deevnet.builder`) and `make discover` (`deevnet.mgmt`) |
| **Risk** | Low. Most likely to go wrong: an update breaks a service, found by its check and undone from the VM's snapshot |
| **Related changes** | [CHG-0093](/docs/changes/2026/0093-service-vms-virtio-scsi/), which moved the VMs off the LSI controller first; [CHG-0083](/docs/changes/2026/0083-patch-pilot/), whose method this follows; [CHG-0082](/docs/changes/2026/0082-update-watcher/), whose report lists what is waiting; [CHG-0092](/docs/changes/2026/0092-builder-repave-f44/), which rebuilt the Builder on Fedora 44 |
| **Related incidents** | [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/) (bulk transfers across the core router), [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) (an LSI controller's panic under disk load), [INC-0007](/docs/incidents/2026/0007-api-sealed-after-power-on/) (the API after OpenBao restarts sealed) |
| **Related runbooks** | [Patching](/docs/runbook/substrate/lifecycle/patching/), [Patch Tools for Claude](/docs/runbook/substrate/lifecycle/patch-tools-for-claude/) |

---

## Summary

**The update watcher's scan of 2026-11-26 20:42 UTC shows a Critical advisory waiting on six of
the seven service VMs, and Important ones on them and on the Builder.** Every Fedora host is on
Fedora 44, supported until 2027-06-02, so these are updates within the release:

| Host | Waiting | Security | Critical / Important |
|---|---|---|---|
| `dv02idn001v01` | 140 | 56 | 1 / 23 |
| `dv02msg001v01` | 140 | 56 | 1 / 23 |
| `dv02nms001v01` | 140 | 56 | 1 / 23 |
| `dv02obs001v01` | 138 | 57 | 1 / 23 |
| `dv02col001v01` | 136 | 56 | 1 / 23 |
| `dv02prv001v01` | 115 | 54 | 1 / 21 |
| `dv00bld001p01` | 9 (2 major) | 6 | 0 / 2 |

- **Critical, FEDORA-2026-0609e13c0d:** `ca-certificates`, on all six service VMs.
- **Important, on the six:** `python3`, `pcre2`, `sudo`, `util-linux`, `libbrotli`, `dnf5`, and
  `openssl` (all but `dv02prv001v01`).
- **Important, on the Builder:** FEDORA-2026-e07b537eda, `firefox` 160 → 161 (the two majors).
- **A kernel on every host**, so every host reboots.

**Each host is patched as CHG-0083 patched `dv02obj001v01`:** snapshot, throttled download with a
watchdog across the core router, install, reboot. One change from it, its follow-up: the install runs
from the cache (`-C`), so no `dnf` step fetches unthrottled.

**The VMs are patched on VirtIO SCSI.** CHG-0083 left these six for after their disk controllers
moved off the emulated LSI 53C895A that panicked in INC-0006
([ADR-0046](/docs/architecture/decisions/substrate/0046-vm-hardware-profile/)). CHG-0093 moved them
first, so the install's disk load no longer runs through that driver.

## Goal

- The update watcher reports the Builder and the six VMs with no Critical or Important advisory
  waiting, and nothing waiting at all except anything published after the download.
- Every host runs the newest kernel it installed.
- The health watcher shows no problem for any of the seven, and every service answers as it did
  before.
- No ping missed across the core router while anything downloads.

## Scope

**In scope:** Fedora 44 updates, within the release, on the Builder and on `dv02nms001v01`,
`dv02col001v01`, `dv02msg001v01`, `dv02obs001v01`, `dv02idn001v01` and `dv02prv001v01`.

**Out of scope:**
- `dv02obj001v01`: nothing waiting.
- `dv02bld001v01`: the temporary builder, to be destroyed under CHG-0092.
- The hypervisors: 33 updates each, 6 from Debian's security suite, without a severity. That needs
  a change of its own, with the VMs shut down first.
- The core router, switch and AP: not yet checked (no discovery report; no view-only Omada client).
- The disk controller move: CHG-0093, before this.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A VM stalls under the install's disk load | the six VMs, all on `dv02hyp001p01`'s data disk | One VM at a time, nothing else loading the disk, on VirtIO SCSI with IO Thread since CHG-0093. The operator watches the install. A VM that stops answering is screendumped (`qm monitor <vmid>`, `screendump`) before it is reset, then rolled back to its snapshot |
| The download hangs the core router | `dv02cor002p01` | Every `dnf` step that fetches carries `--setopt=throttle=1M`, and the install runs from the cache (`-C`). A watchdog pings `1.1.1.1` across the router throughout |
| An update breaks a service | any VM | The snapshot. Rolling back also loses whatever the VM wrote since: for `dv02prv001v01`, the API's database. So each VM's rollback is decided right after its checks, not later |
| OpenBao restarts sealed | `dv02idn001v01` | Expected ([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/)). Since CHG-0084 the egress list answers while it is sealed. Unseal it only if the work session needs it |
| The control node does not come back | `dv00bld001p01` | Patched first, while `dv02bld001v01` still exists to fall back to. No snapshot: the undo is the previous kernel at the GRUB menu, and `dnf history undo` |
| A guest reboot hangs | any VM | Proxmox console. `qm stop` then `qm start` only after a screendump |

## Prerequisites

- [ ] The update watcher's latest report shows the counts above, or close to them: a fresh scan (`refresh_updates`, or `make update-watch-now`)
- [ ] Nothing else running on `dv02hyp001p01`'s data disk: no backup, no restore, no copy
- [ ] CHG-0093 complete: the six VMs on `scsihw: virtio-scsi-single`
- [ ] `dv02bld001v01` still running, as a fallback control node through Step 2
- [ ] The operator at the Builder, able to reach `dv02hyp001p01`'s console

## Procedure

Every VM step runs from the Builder as `a_autoprov`. `<vm>` is the VM's inventory name and `<vmid>`
its VMID on `dv02hyp001p01`.

### Step 1: Record where it starts

No outage.

**Run:** `make discover` (in `deevnet.mgmt`); `make health-watch-now` (in `deevnet.builder`). Keep
`/srv/updates/latest.txt` and `/srv/health/latest.txt` as they stand.

**Verify:** every system answers; the health watcher's only problems, if any, are written down here.

### Step 2: The Builder

Its reboot ends the operator's session. Nothing else depends on it while it is down.

**Run,** on the Builder:

1. **Watchdog,** in a second session: `ping -i 2 1.1.1.1`.
2. **Download:** `sudo dnf -y --setopt=throttle=1M upgrade --downloadonly`.
3. **Install:** `sudo dnf -y -C upgrade`.
4. **Reboot if needed:** `sudo dnf needs-restarting -r`; if a reboot is needed, `sudo reboot`.

**Verify:** the watchdog missed nothing; `uname -r` is the newest installed kernel;
`dnf check-upgrade` lists nothing; `systemctl --failed` is empty; the update and health watchers' timers
are active; `make patch-mcp-test` passes.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: Each service VM, one at a time

In this order, least depended on first: `dv02nms001v01` (204), `dv02col001v01` (206),
`dv02msg001v01` (205), `dv02obs001v01` (207), `dv02idn001v01` (200), `dv02prv001v01` (201). The next VM
starts only after the one before has passed its checks.

**Run:**

1. **Before:** on the VM, `systemctl --failed` and `sudo podman ps` (or the VM's service units);
   write down what is running.
2. **Snapshot,** on `dv02hyp001p01`:
   `qm snapshot <vmid> pre-chg-0094 --vmstate 0 --description "CHG-0094"`.
3. **Watchdog,** on the VM in a second session: `ping -i 2 1.1.1.1`.
4. **Download,** on the VM: `sudo dnf -y --setopt=throttle=1M upgrade --downloadonly`.
5. **Install:** `sudo dnf -y -C upgrade`. Watch it; if the VM stops answering, see the guard above.
6. **Reboot if needed:** `sudo dnf needs-restarting -r`; if a reboot is needed, `sudo reboot`.

**Verify,** for each VM:

1. The watchdog missed nothing during the download.
2. The VM is back on the newest kernel; `dnf check-upgrade` lists nothing; `systemctl --failed` is
   empty; what ran before runs again.
3. Its own service answers:

| VM | Check |
|---|---|
| `dv02nms001v01` | The Omada controller's web interface answers, and it shows the switch and AP connected |
| `dv02col001v01` | Logs and metrics still arrive in the observability store: a new entry after the reboot |
| `dv02msg001v01` | The MQTT broker accepts a client again, and the log bridge's unit is active |
| `dv02obs001v01` | The log and metrics stores and the dashboard answer through the service proxy |
| `dv02idn001v01` | OpenBao answers its status, sealed. Tenant DNS answers a query for a tenant zone |
| `dv02prv001v01` | `make health-watch-now` shows "Deevnet API alive" and "Deevnet API database" ok. The egress agent on `dv02hyp002p02` succeeds on its next run. `s3` and `tfstate` answer through the service proxy |

4. `make health-watch-now` shows no new problem.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: The watcher and the catalog

**Run:** `make update-watch-now` and `make update-watch-ack` (in `deevnet.builder`); `make discover`
(in `deevnet.mgmt`).

**Verify:** the report shows the seven hosts with no Critical or Important advisory waiting. The
Software Catalog updated from the discovery report wherever a version it records changed.

### Step 5: Drop the snapshots

Three days later, if nothing has gone wrong: on `dv02hyp001p01`,
`qm delsnapshot <vmid> pre-chg-0094` for 204, 206, 205, 207, 200 and 201.

## Verification

The four points under Goal.

## Undo

### Undo Step 2

Reboot and choose the previous kernel at the GRUB menu. For a package that broke something,
`sudo dnf history undo last` (it needs the old packages from the mirrors). If the Builder cannot be
brought back, `dv02bld001v01` is the control node until it is.

### Undo Step 3

On `dv02hyp001p01`: `qm stop <vmid>`, `qm rollback <vmid> pre-chg-0094`, `qm start <vmid>`. Anything
the VM wrote after the snapshot is lost. For `dv02prv001v01` that is the API's database, so its
rollback is decided as soon as its checks fail, not later. Undo stops being practical once the
snapshot is dropped in Step 5.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: discovery report and health state taken
- [ ] Step 2: the Builder updated, rebooted, its watchers and `deevnet-patch` working
- [ ] Step 3: the six VMs updated and rebooted, each one's service answering, no ping missed
- [ ] Step 4: the watcher shows no Critical or Important advisory on the seven hosts; catalog updated
- [ ] Step 5: the six snapshots dropped, three days or more after
- [ ] For an Upgrade: `make discover` (`deevnet.mgmt`) run after it, and the Software Catalog updated from its report

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] A change record for the hypervisors' waiting updates (33 each, 6 security, without a severity)
