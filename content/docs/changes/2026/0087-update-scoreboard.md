---
title: "CHG-0087: The Update Scoreboard"
weight: -87
---

# CHG-0087: The Update Scoreboard

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-24** |
| **Window** | No outage. A quarter of an hour, operator at the Builder |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the update watcher); every substrate service VM, both Builder VMs and both hypervisors (`deevnet-watch-check`) |
| **Automation** | `deevnet.builder` `make update-watch`; `deevnet.mgmt` `site.yml --tags update_check` |
| **Risk** | Low. Most likely to go wrong: the changed check stops answering on a host, found by the dry run in Step 3 |
| **Related changes** | [CHG-0082](/docs/changes/2026/0082-update-watcher/), which built the update watcher; [CHG-0086](/docs/changes/2026/0086-health-watcher/), whose health watcher asks the same check |
| **Related incidents** | None |
| **Related runbooks** | [Patching](/docs/runbook/substrate/lifecycle/patching/#updates-waiting) |

---

## Summary

**The update watcher's login banner becomes a scoreboard: a row per system, grouped as service VMs,
Builder, hypervisors and network, counting the updates waiting as major or minor, and how many of
them fix a security advisory.** Systems with news not yet acknowledged are marked `new`. The banner
used to list the day's news line by line, and stopped after six lines. `latest.txt` and the dated
reports lead with the same table (`deevnet.builder`
[#45](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/45)).

| Column | Counts |
|---|---|
| Major | updates that change the epoch or the first version field: kernel 6.17 to 7.3. A first field that is a date (linux-firmware, tzdata) does not count |
| Minor | every other update. Major and Minor together are every update waiting |
| Security | the updates, of either kind, that fix a security advisory |

To tell major from minor the watcher needs the version each update replaces. `deevnet-watch-check`'s
`updates` check now also prints the installed versions on Fedora; Proxmox VE's package list already
gives them. What is news, and when the banner shows, does not change.

## Goal

- The banner and `latest.txt` show the scoreboard, every update on every host sorted into major or
  minor.
- The update watcher and the health watcher still answer on every host.

## Procedure

### Step 1: The watcher, and the check on the Builder VMs and hypervisors

**Run** (in `ansible-collection-deevnet.builder`):

```bash
make publish        # deevnet.builder at the user level, for deevnet.mgmt in Step 2
make update-watch
```

### Step 2: The check on every service VM

**Run** (in `ansible-collection-deevnet.mgmt`):

```bash
make install-dev
ansible-playbook playbooks/site.yml --tags update_check
```

### Step 3: A dry run

**Run:** `make update-watch-dry-run` and `make health-watch-dry-run`.

**Verify:** the scoreboard lists every host under its kind, none with updates left unsorted; every
host answers both watchers.

## Undo

Revert #45 and run Steps 1 and 2 again.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the watcher and the check on the Builder VMs and hypervisors
- [x] Step 2: the check on every service VM
- [x] Step 3: the scoreboard complete, both watchers answered everywhere
- [x] The Patching runbook describes the scoreboard

## Outcome

**The update watcher's banner and reports show the scoreboard, every update on every answering host
sorted into major or minor.** All commands ran from the Builder, the operator's session supplying the
automation key.

| When | Steps | What happened |
|---|---|---|
| 07:31–07:32 | Step 1 | `make publish`, `make update-watch`: the watcher's script and config on the Builder; the check on both Builder VMs and both hypervisors. No failure |
| 07:32 | Step 2 | `site.yml --tags update_check`: the check on all seven service VMs. No failure |
| 07:33 | Step 3 | The update watcher's dry run: every host under its kind, nothing unsorted (27 major, 1,661 minor, 702 security). The health watcher's: all fifteen checks pass |
| 07:33 | | `make update-watch-now`: the banner shows the scoreboard |

`dv02bld002v01` answered the check but could not report its updates, as before this change: dnf on
that VM cannot open its lock file as the watcher's account. The scoreboard shows it as not answering.

## Follow-ups

- [ ] `dv02bld002v01`: dnf cannot open `/usr/lib/sysimage/libdnf5/system-repo.lock` as `deevnet-watch`, so the update watcher gets no answer from it
