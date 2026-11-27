---
title: "CHG-0101: The VM Hardware Profile Verified at Build and Watched"
weight: -101
---

# CHG-0101: The VM Hardware Profile Verified at Build and Watched

| | |
|---|---|
| **Date** | 2026-11-27 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-27** |
| **Window** | No service outage. The API restarts once for 0.30.0 (seconds). `dv02col001v01` is down while it is rebuilt; it runs nothing but its operating system |
| **Site** | mobile |
| **Systems** | `proxmox_vm` and `deevnet_api` (`deevnet.mgmt`); the Deevnet API on `dv02prv001v01`; the health watcher on `dv00bld001p01`; `dv02hyp001p01` and `dv02hyp002p02`; `dv02col001v01` |
| **Automation** | `deevnet.mgmt` `site.yml` (`deevnet_api`, the collector's VM); `deevnet.builder` `make update-watch`, `make health-watch`, `make host-keys` |
| **Risk** | Low. Most likely to go wrong: the new check in `proxmox_vm` refuses the collector's clone, found by the rebuild itself, before the VM starts |
| **Related changes** | [CHG-0098](/docs/changes/2026/0098-vm-builders-apply-profile/) (the builders apply the profile), [CHG-0100](/docs/changes/2026/0100-tenant-vms-vm-profile/) (the last VMs moved) |
| **Related incidents** | [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) |
| **Related runbooks** | [Health Watcher](/docs/runbook/substrate/recovery/health-watcher/), [SSH Host Keys](/docs/runbook/substrate/lifecycle/host-keys/) |

---

## Summary

**ADR-0046 has three "To accept" items left, and this change does all three.**

- **The builders check what they built.** `proxmox_vm` puts a VM it has just made through the
  comparison `make vm-profile` uses, before its first start. The API reads a new workload's
  configuration back and checks the controller and boot-disk options. A VM off the profile is not
  started.
- **A service VM is built from the new template.** `dv02col001v01` is rebuilt from
  `fedora-server-44-1.7` (VMID 101 on `dv02hyp001p01`). It runs nothing but its operating system, so
  the rebuild costs no service, and it is the first VM `proxmox_vm`'s new check runs on.
- **The check runs unattended and alerts.** A root timer on each hypervisor writes only the
  profile's parts of each VM's configuration to a file, and the watcher's pinned key reads it
  (`deevnet-watch-check vm-hardware`). No token or secret is added. The health watcher compares every
  VM with the profile every five minutes, more often than the ADR's "daily", and raises drift on its
  login banner. Its comparison is the one `make vm-profile` uses, moved to `deevnet.builder` so the
  two cannot disagree.

## Goal

- `proxmox_vm` and the API refuse to start a VM they made off the profile.
- `dv02col001v01` runs on a clone of the new template, compliant.
- The health watcher reports the profile check on every run, and raises drift.
- ADR-0046 accepted.

## Scope

| Repository | Pull request | What |
|---|---|---|
| `deevnet.mgmt` | [#149](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/149) | `proxmox_vm`'s check; the `vm_profile_check` filter uses the shared comparison; `deevnet_api_version` to 0.30.0 |
| `deevnet-provisioning-api` | [#89](https://github.com/deevnet/deevnet-provisioning-api/pull/89) | The read-back and check; released as 0.30.0 |
| `deevnet.builder` | [#64](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/64) | The shared comparison (`plugins/module_utils/vm_profile.py`); `proxmox_node_vm_report`; `deevnet-watch-check vm-hardware`; the watcher's check |

## Risk and impact

| Risk | Mitigation |
|---|---|
| `proxmox_vm`'s check refuses a good clone | Tested on compliant, drifting and excepted read-backs; the collector's rebuild is its first real run, on a VM nothing depends on |
| The API refuses good workloads after 0.30.0 | Tested against a fake node that applies the profile and one that ignores it. An adopted workload is never checked |
| The watcher raises noise | A problem needs two failed runs in a row, as for every check. A stale or missing report is one problem, not one per VM |
| The report exposes VM configuration | It holds only the controller, CPU, firmware, machine, agent, disks and NICs: no cloud-init, description or keys |

## Procedure

### Step 1: Merge and release

**Run:** merge the three pull requests. `make publish` in both collections. Tag `v0.30.0` on #89's
merge commit and `make stage`.

### Step 2: The hypervisors' report and the watcher

**Run:** `make update-watch`, then `make health-watch`, in `deevnet.builder`.

**Verify:** `/var/lib/deevnet-vm-hardware/vms.json` on each hypervisor is fresh. `make
health-watch-now` lists `ok <hypervisor> VM hardware report` for both. A dry run against a copy of
its configuration whose profile asks for another controller lists every VM as drift.

### Step 3: The API on 0.30.0

**Run** (OpenBao open): the `deevnet_api` play.

**Verify:** the API logs `v0.30.0`; `make reconcile` for each tenant completes.

### Step 4: Rebuild the collector

**Run:** `qm destroy 206 --purge` on `dv02hyp001p01`. Then, the operator (the build reads the
hypervisor's API token from the vault):

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --limit dv02col001v01
```

Then its new host keys: `make host-keys LIMIT=dv02col001v01` in `deevnet.builder`, a pull request
in the inventory, and `make host-keys-install` after the merge.

**Verify:** the play's "is on the VM hardware profile" check passes before it starts the VM; it is a
clone of VMID 101; `make vm-profile` reports it compliant; SSH to it by name works from the record.

### Step 5: Accept ADR-0046

Its last three items ticked, its open question answered, its status Accepted.

## Undo

Each code change is reverted by pull request. The API goes back to 0.29.0 by its pin. The watcher's
check is removed with its role and the hypervisors' timer disabled. A collector that will not build
is built again from the previous template's successor, or left down: nothing depends on it.

## To close

**This change closes when every item below is done.**

- [x] Step 1: merged, published, 0.30.0 staged
- [x] Step 2: the report on both hypervisors; the watcher reports the check and raises drift
- [x] Step 3: the API on 0.30.0, the reconciles completed
- [x] Step 4: the collector rebuilt from the new template, compliant, its keys recorded
- [x] Step 5: ADR-0046 accepted

## Outcome

**ADR-0046 is accepted.** Both builders check what they build, the collector runs on a clone of the
new template, and the health watcher checks every VM against the profile every five minutes. The
rebuild also showed the host-key record working: the watcher raised the rebuilt collector's changed
key, and cleared it once its new keys were merged.

| When (UTC) | Steps | What happened |
|---|---|---|
| Before Step 1 | Tests | `proxmox_vm`'s check: compliant and declared-exception read-backs pass, an `lsi` one fails naming the controller. The API: `go test ./...`, with a node that ignores the profile leaving the workload unstarted. The watcher with fake reports: compliant and excepted VMs pass, `lsi` flagged, a stale, missing or unread report flagged, an unanswered host's problems kept. `make vm-profile` through the moved comparison: unchanged, 14 compliant, 1 declared exception |
| Before 20:56 | 1 | Merged: [deevnet.mgmt #149](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/149), [deevnet-provisioning-api #89](https://github.com/deevnet/deevnet-provisioning-api/pull/89), [deevnet.builder #64](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/64). `make publish` in both collections; `v0.30.0` tagged on `d8bcf6c` and staged |
| 20:56 | 2 | `make update-watch`: the report's role on both hypervisors (5 changed each); `make health-watch`. Each `vms.json` seconds old, holding only `scsihw`, `cpu`, `bios`, `machine`, `agent`, the disks and the NICs. `make health-watch-now`: `ok` for both hypervisors' VM hardware report, all well |
| 20:56 | 2 | A dry run against a copy of the watcher's configuration whose profile asks for `lsi`: all 15 VMs listed as failing, each naming `scsihw: is virtio-scsi-single, profile lsi`. Nothing written |
| 20:56 | 4 | `dv02col001v01`'s configuration saved (`/root/chg-0101-206.conf`); shut down and destroyed with its disk and its `pre-chg-0094` snapshot. Its old keys removed from the operator's `known_hosts` |
| Before 21:05 | 4 | The operator: `site.yml --limit dv02col001v01`. VMID 206 cloned from VMID 101 (`qmclone:101 … OK`). The play started it, which it does only after "is on the VM hardware profile" passes. `make vm-profile`: `206 dv02col001v01: COMPLIANT`; 15 VMs, 14 compliant, 1 declared exception, 0 drift |
| 21:05–21:36 | 4 | The watcher raised `dv02col001v01 answers: Host key verification failed` (the record still held the old VM's keys). `make host-keys LIMIT=dv02col001v01`: all three keys `CHANGED`, the new fingerprints matching the host's own key files; [ansible-inventory-deevnet #139](https://github.com/deevnet/ansible-inventory-deevnet/pull/139) merged; `make host-keys-install`. The watcher cleared it at 21:36. SSH by name with no user `known_hosts`: kernel 7.3.6, `virtio_scsi` loaded, `running` |
| 21:35 | 3 | The operator, OpenBao open: the `deevnet_api` play. The API logs `version v0.30.0 commit d8bcf6c`. `make reconcile` for `tdemo`, `eds`, `cdeever`: each reconciled |
| 21:36 | 2 | `make health-watch-now`: all well |
| After 21:36 | 5 | ADR-0046 accepted |

### Departures from the plan

- **The check runs every five minutes, not daily** as ADR-0046 first said: it rides the health
  watcher, whose runs are five minutes apart. The ADR's open question records it.
- **Step 4's check was confirmed by the play starting the VM,** not from its output, which Ansible
  does not log here: a failed check stops the play before it starts the VM.
