---
title: "CHG-0088: The Builder VMs Made Inactive"
weight: -88
---

# CHG-0088: The Builder VMs Made Inactive

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Change type** | Decommission |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-24** |
| **Window** | No outage. Half an hour, operator at the Builder |
| **Site** | mobile |
| **Systems** | `dv02bld001v01` (VMID 202) and `dv02bld002v01` (VMID 203) on `dv02hyp001p01`; the core router's DNS and DHCP; the update and health watchers on `dv00bld001p01` |
| **Automation** | `deevnet.net` `dns.yml`, `dhcp.yml`; `deevnet.builder` `make update-watch`, `make health-watch`; `qm` on `dv02hyp001p01` |
| **Risk** | Low. Most likely to go wrong: destroying the wrong VMID, guarded by checking each VMID's name before it is destroyed |
| **Related changes** | [CHG-0042](/docs/changes/2026/0042-rehome-stray-vms/), the last VMs destroyed on `dv02hyp001p01` |
| **Related incidents** | None |
| **Related runbooks** | [Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/), which builds `dv02bld001v01` when it is needed |

---

## Summary

**The two Builder VMs on the management hypervisor are destroyed and kept in inventory as inactive:
declared, not built.** Neither is in use. `dv02bld001v01` is the temporary builder that repaving the
Builder stands up; `dv02bld002v01` proved the UEFI PXE install path. Both run all the time, are patched
and watched, and hold nothing that is not elsewhere: `dv02bld001v01`'s checkouts are clean and pushed,
and its `/srv/deevnet-http` is a partial copy of the Builder's.

A new inventory group, `inactive`, holds hosts that are declared but not built
(`ansible-inventory-deevnet` [#124](https://github.com/deevnet/ansible-inventory-deevnet/pull/124)):

| | An inactive host |
|---|---|
| Groups | In `inactive` and no other, so no play builds or configures it. A comment beside it lists the groups it rejoins when made active |
| DNS and DHCP | No record and no reservation: the router roles delete them (`deevnet.net` [#56](https://github.com/deevnet/ansible-collection-deevnet.net/pull/56), `deevnet.builder` [#46](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/46)) |
| Identity | Kept: its VMID and MAC stay declared and reserved, so it comes back with the same address |
| host_vars | Kept unchanged but for a line saying it is inactive |
| PXE | `dv02bld002v01`'s per-MAC GRUB config stays on the Builder, so it can be reinstalled as before |

Making one active again is moving it back into its groups and building it, as before. The temporary
builder's address leaves OpenBao's list of where Ansible's AppRole may log in from; it goes back when
the temporary builder is next needed.

## Goal

- VMIDs 202 and 203 are gone from `dv02hyp001p01`, with every disk.
- Neither name resolves, and neither has a DHCP reservation.
- The VM identity audit passes with both identities still declared.
- The update and health watchers no longer ask either host, and every host they ask answers.

## Prerequisites

- [x] `deevnet.net` #56, `deevnet.builder` #46, the inventory's #124 and this record merged

## Procedure

### Step 1: The watchers stop asking

**Run** (in `ansible-collection-deevnet.builder`, the inventory at `main`):

```bash
make publish
make update-watch
make health-watch
```

**Verify:** `/etc/deevnet/update-watch.json` and `health-watch.json` list neither host.

### Step 2: Shut down and destroy

On `dv02hyp001p01`, for VMID 202 and then 203:

```bash
qm config <vmid> | grep ^name     # dv02bld001v01, dv02bld002v01
qm shutdown <vmid> --timeout 120
qm destroy <vmid> --purge --destroy-unreferenced-disks 1
```

**Verify:** `qm list` lists neither; `lvs` shows no `vm-202-` or `vm-203-` volume.

### Step 3: DNS and DHCP

**Run** (in `ansible-collection-deevnet.net`), each after a `--check` that deletes only these two
hosts' records:

```bash
ansible-playbook playbooks/dns.yml
ansible-playbook playbooks/dhcp.yml
```

**Verify:** neither name resolves through the core router; the Kea reservations hold neither MAC
(`02:de:20:00:00:ca`, `02:de:20:00:00:cb`).

### Step 4: Known hosts

On the Builder, remove both hosts' keys from the operator's and `deevnet-watch`'s `known_hosts`
(`ssh-keygen -R` by name and address), so a rebuilt host is not refused for a changed key.

### Step 5: Check

**Run:** `ansible-playbook playbooks/vm-identity.yml` (`deevnet.mgmt`), `make update-watch-dry-run` and
`make health-watch-dry-run` (`deevnet.builder`).

**Verify:** the audit passes, declaring VMIDs 202 and 203, with neither in use; both watchers' hosts all
answer.

## Undo

The VMs are not restored: each is rebuilt by making it active again
([Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/), Step 1, for
`dv02bld001v01`). Reverting #124 and running Steps 1 and 3 returns everything else.

## To close

**This change closes when every item below is done.**

- [x] Step 1: neither host in either watcher's configuration
- [x] Step 2: VMIDs 202 and 203 destroyed, no volume left
- [x] Step 3: no DNS record or DHCP reservation for either
- [x] Step 4: both removed from the Builder's known hosts
- [x] Step 5: the identity audit and both watchers pass
- [x] The runbook says what an inactive host is and how one is made active; pages that describe either
  VM as running say it is inactive

## Outcome

**Both VMs are destroyed with their disks, and both stay in inventory as inactive, their identities
reserved.** All commands ran from the Builder, the operator's session supplying the automation key.

| When | Steps | What happened |
|---|---|---|
| 08:08–08:10 | Step 1 | `make publish`, `make update-watch`, `make health-watch`: both watchers' configurations list neither host. No failure |
| 08:10 | Step 2 | VMID 202 named `dv02bld001v01`, 203 `dv02bld002v01`, checked before each was touched. Each shut down cleanly (203 has no guest agent, and stopped on ACPI) and was destroyed with `--purge`: `vm-202-cloudinit`, `vm-202-disk-0` (64G), `vm-202-disk-1` (250G), `vm-203-disk-0` (EFI) and `vm-203-disk-1` (100G) removed. `qm list` and `lvs` show neither |
| 08:12 | Step 3 | After `--check` runs naming only these two hosts: `dns.yml` deleted their two host overrides, `dhcp.yml` their two reservations. Nothing else changed. Neither name resolves through the core router, forward or reverse |
| 08:12 | Step 4 | Both names and addresses removed from the operator's and `deevnet-watch`'s `known_hosts` |
| 08:13 | Step 5 | The VM identity audit passes, declaring VMIDs 202 and 203 with neither in use. The health watcher: all well. The update watcher's scoreboard lists neither host |

## Follow-ups

- [ ] OpenBao's AppRole CIDRs without `10.20.99.97`: applied by the `openbao` role at the next work
  session
