---
title: "CHG-0082: The Update Watcher"
weight: -82
---

# CHG-0082: The Update Watcher

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Planned** |
| **Window** | No outage. An hour, operator at the Builder |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the watcher); every substrate service VM, both Builder VMs and both hypervisors (the read-only account); the Omada controller (a view-only client) |
| **Automation** | `deevnet.builder`: roles `update_watch` and `update_check`, `make update-watch`. `deevnet.mgmt`: `site.yml --tags update_check`. Inventory: group `update_watchers` |
| **Risk** | Low. Most likely to go wrong: the watcher's key works more widely than meant, found by the lockdown checks in Step 5 |
| **Related changes** | [CHG-0079](/docs/changes/2026/0079-proxmox-notifications/) (the hypervisors' mail, which the Builder's follows) |
| **Related incidents** | [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/) (bulk transfers across the core router) |
| **Related runbooks** | [Patching](/docs/runbook/substrate/lifecycle/patching/) |

---

## Summary

**The operator is to be told by email when an update is waiting anywhere in the substrate, without
having to look** ([Patch Management](/docs/roadmap/infrastructure/substrate/patch-management/) v2).
Today waiting updates are found only by running `make discover`, which needs the operator's own
session: the automation key exists only in the operator's forwarded agent, there is no vault
password file, and OpenBao is sealed between work sessions.

This change deploys a watcher on the Builder that runs once a day with credentials of its own that
can only read:

- **On every host it asks, an account that runs one program.** `deevnet-watch`, with no sudo and no
  password, whose key is pinned to `deevnet-update-check` with `command=`, `restrict` and `from=` the
  Builder, as the broker and log writers' keys are. The check reads the package manager's cache
  (`dnf -C` on Fedora, `apt` on Proxmox VE), which each host's own timer keeps fresh, so it
  downloads nothing.
- **For the Omada controller, a view-only Open API client**, to read each device's latest firmware.
- **For the core router, nothing.** OPNsense's only firmware privilege also allows installing
  updates and rebooting, so the router is watched upstream instead: OPNsense's release tags against
  the version the newest discovery report saw.

The watcher mails, through the Builder's own send-only Postfix, what is new: a security update, a
host newly behind, a new OPNsense release or device firmware, a system that stopped answering, and a
reminder for anything waiting 30 days. The hypervisors are asked but not mailed about: Proxmox VE
mails its own.

## Goal

- Every substrate service VM, both Builder VMs and both hypervisors answer the watcher, and refuse
  its key for anything but the check, and from anywhere but the Builder.
- The first run's mail arrives; a second run sends nothing.
- The timer runs the next day on its own.

## Scope

**In scope:** the `deevnet-watch` account and check on those hosts; Postfix, the watcher, its
account, key, configuration and timer on the Builder; a view-only Omada client.
**Out of scope:** applying any update; the access switch and the Omada controller's own version,
which the watcher cannot read (Patch Management v3); the Pi lab.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The watcher's key logs in to more than the check | every host it asks | `command=` and `restrict` on the key, no sudo, and the checks in Step 5 |
| The key is used from somewhere else | every host it asks | `from=` the Builder's address; Step 5 tries it from another host |
| The check downloads metadata across the core router | the router | It reads the cache only (`dnf -C`; `apt` reads its lists) |
| The Builder becomes a mail relay | the Builder | Postfix listens on loopback only and relays for no network |
| A watcher credential leaks | the Omada controller | The client is view-only; the SSH key reads only waiting updates |

## Prerequisites

- [ ] The pull requests for the inventory, `deevnet.builder`, `deevnet.mgmt` and this record merged
- [ ] A view-only Open API client made in the Omada controller (role: viewer, for the watcher alone), and its id and secret in the inventory's vault as `vault_omada_watch_client_id` and `vault_omada_watch_client_secret`
- [ ] At least one discovery report in `/srv/discovery` (`make discover`), for the router's version

## Procedure

### Step 1: The watcher on the Builder

No outage.

**Run** (in `ansible-collection-deevnet.builder`):

```bash
make publish        # deevnet.builder at the user level, for deevnet.mgmt in Step 3
make update-watch
```

**Verify:** `systemctl list-timers deevnet-update-watch.timer` lists it; `/etc/deevnet/update-watch.pub`
holds an `ssh-ed25519` key; `postconf inet_interfaces` is `loopback-only`.

### Step 2: The check on the Builder VMs and hypervisors

Done by Step 1's `make update-watch`, which also runs `update_check` on `builder` and `hypervisors`.

**Verify:** `id deevnet-watch` on `dv02bld001v01` and on each hypervisor.

### Step 3: The check on every service VM

No outage.

**Run** (in `ansible-collection-deevnet.mgmt`):

```bash
make install-dev
ansible-playbook playbooks/site.yml --tags update_check
```

**Verify:** `id deevnet-watch` on each management-plane VM.

### Step 4: A dry run

**Run:** `make update-watch-dry-run` (in `deevnet.builder`).

**Verify:** every host answers; the AP's firmware is read; OPNsense is compared with the newest
discovery report; the mail reads right.

### Step 5: The key is locked down

On one service VM and one hypervisor, from the Builder as `deevnet-watch`:

1. `ssh deevnet-watch@<host> id` prints the check's output, not `id`'s: the command is forced.
2. `ssh -t deevnet-watch@<host>` gets no terminal.
3. The same key copied to another host and used from there is refused.
4. On the host, `sudo -l -U deevnet-watch` lists nothing.

Afterwards, the copied key is deleted.

### Step 6: The first real run

**Run:** `make update-watch-now`.

**Verify:** the mail arrives. A second `make update-watch-now` logs `0 new; mail not needed`.

## Verification

The three points under Goal, the last the next day: `systemctl list-timers` shows the timer ran,
and nothing was mailed again.

## Undo

On the Builder: `systemctl disable --now deevnet-update-watch.timer`, then remove the units,
`/usr/local/sbin/deevnet-update-watch`, `/etc/deevnet/update-watch.*` and the `deevnet-watch`
account and home; remove Postfix if nothing else uses it. On every host the check went to:
`userdel -r deevnet-watch` and remove `/usr/local/sbin/deevnet-update-check`. In the Omada
controller: delete the view-only client. Then remove the roles from both `site.yml`s.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: the watcher, its timer and Postfix on the Builder
- [ ] Step 2: the check on the Builder VMs and hypervisors
- [ ] Step 3: the check on every service VM
- [ ] Step 4: a dry run with every host answering
- [ ] Step 5: the key refused for anything but the check, from anywhere but the Builder
- [ ] Step 6: the first mail received; a second run sends nothing
- [ ] Verification: the timer's first run on its own, with nothing mailed again
- [ ] The runbook's Patching page says what the watcher mails and how to run it now
- [ ] Patch Management v2 marked done

## Outcome

To be written when the change has run.

## Follow-ups

None yet.
