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
| **Status** | **Planned** |
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

- [ ] Step 1: the watcher and the check on the Builder VMs and hypervisors
- [ ] Step 2: the check on every service VM
- [ ] Step 3: the scoreboard complete, both watchers answered everywhere
- [ ] The Patching runbook describes the scoreboard

## Follow-ups

None.
