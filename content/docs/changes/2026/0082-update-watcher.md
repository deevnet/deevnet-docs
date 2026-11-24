---
title: "CHG-0082: The Update Watcher"
weight: -82
---

# CHG-0082: The Update Watcher

| | |
|---|---|
| **Date** | 2026-11-23 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete, 2026-11-24** |
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

- [x] Step 1: the watcher and its timer on the Builder (Postfix installed, then removed: see Departures)
- [x] Step 2: the check on the Builder VMs and hypervisors
- [x] Step 3: the check on every service VM
- [x] Step 4: a dry run with every host answering
- [x] Step 5: the key refused for anything but the check, with no terminal, no forwarding and no sudo
- [x] Step 6: the first report and banner written; a second run finds nothing new
- [x] Verification: the timer's first run on its own, finding nothing new
- [x] The runbook's Patching page says what the watcher reports and how to run it now
- [x] Patch Management v2's watcher tasks marked done (v2 itself waits for the Omada client: see Follow-ups)

## Outcome

**The watcher runs on the Builder and every substrate host answers it; it reports in `/srv/updates`
and at login, not by mail.** All commands ran from the Builder, the operator's session supplying the
automation key. Times are to the minute from the session, not a log, except Step 6's, which are
the watcher's journal.

| When | Steps | What happened |
|---|---|---|
| 18:17 | Step 1, 2 | `make update-watch`: the watcher, its key, the timer and Postfix on the Builder; the check and account on both Builder VMs and both hypervisors. No failure |
| 18:20 | Step 1 | `main.cf` held `mydestination` twice: the role's `lineinfile` had replaced a commented line, not the active one. The role now uses `postconf -X` then `-e`; two more deploys changed nothing |
| 18:22 | Step 3 | `site.yml --tags update_check`: the check and account on all seven service VMs |
| 18:23 | Step 4 | Every host answered. `dv02bld002v01` answered but could not check: its dnf5 (5.4.1, older than the other VMs' 5.4.4 to 5.4.7) cannot take its lock as an unprivileged user. The watcher listed it as up to date with an error beside it; it now counts as not answering |
| 18:25 | Step 5 | On `dv02bld001v01`: asked for `id`, the key ran the check; a terminal was refused; a port forward was refused (`administratively prohibited`). On all eleven hosts: `deevnet-watch` may not run sudo, and holds one key line, with `command=`, `restrict` and `from=` the Builder |
| 18:28 | Step 6 | The first run queued its mail; Postfix could not connect to the operator's provider on port 25 |
| 18:30 | | Outbound port 25 is blocked on the site's current network, to every provider tried, from the Builder and from a hypervisor alike; 587, 465 and 443 pass |
| 18:37 | Step 6 | The report replaced mail (below). The queued mail deleted, Postfix removed from the Builder, the watcher's state reset. The run wrote `latest.txt`, the dated report and the banner: 19 new. A second run: 0 new |
| 2026-11-24 00:24 | Verification | The timer's first run on its own: every host answered, `0 new; 19 pending in the notice` |

What it found on its first run: 1,700 updates waiting across the substrate, about 700 for security,
from 17 on `dv02obj001v01` to 578 on the Builder itself; five security updates on each hypervisor; the
core router on the newest OPNsense point release.

### Departures from the plan

- **A report and a login banner replace mail.** Mail could not leave the site's current network on
  port 25, and a mobile site's network changes under it. The operator chose a report on the Builder:
  `/srv/updates/latest.txt` each run, a dated file of what was new, and a notice that
  `/etc/profile.d/deevnet-updates.sh` prints in every interactive login shell until
  `make update-watch-ack`. Postfix and the mail settings left the role and the inventory.
- **The check was renamed after this change.** [CHG-0086](/docs/changes/2026/0086-health-watcher/) replaced
  `deevnet-update-check` with `deevnet-watch-check`, whose `updates` check is this one.
- **`from=` was checked, not exercised.** Using the key from another host would have meant copying
  the watcher's private key off the Builder, the exposure the restriction exists for. Every host's key
  line carries `from=` the Builder's address instead.
- **No Omada client yet.** The view-only client is not made, so the report says the devices were not
  checked, and Patch Management v2, whose definition of done includes the AP's firmware, is not
  marked done with this change.

## Follow-ups

- [ ] Make the view-only Omada Open API client and put its id and secret in the vault, so the AP's firmware is checked; then mark Patch Management v2 done
- [x] ~~Update dnf5 on `dv02bld002v01`~~: declined, the VM is to be removed ([CHG-0083](/docs/changes/2026/0083-patch-pilot/))
- [ ] The hypervisors' Proxmox notifications also leave by direct mail on port 25 (CHG-0079), which the site's current network blocks: decide how they reach the operator
