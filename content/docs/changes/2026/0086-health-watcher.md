---
title: "CHG-0086: The Health Watcher"
weight: -86
---

# CHG-0086: The Health Watcher

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | **Planned** |
| **Window** | No outage. Half an hour, operator at the Builder |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the watcher); every substrate service VM, both Builder VMs and both hypervisors (a second key on the read-only account) |
| **Automation** | `deevnet.builder`: role `health_watch`, and `update_check` extended, `make health-watch`. `deevnet.mgmt`: `site.yml --tags update_check` |
| **Risk** | Low. Most likely to go wrong: rewriting the read-only account's `authorized_keys` locks the update watcher out of a host, found by its dry run in Step 4 |
| **Related changes** | [CHG-0082](/docs/changes/2026/0082-update-watcher/), whose account and pattern this reuses |
| **Related incidents** | [INC-0007](/docs/incidents/2026/0007-api-sealed-after-power-on/) action 4, [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) action 4, [INC-0002](/docs/incidents/2026/0002-controller-vm-network-hang/) action 3 |
| **Related runbooks** | [Shutdown and Power-On](/docs/runbook/substrate/lifecycle/shutdown-and-power-on/) |

---

## Summary

**Nothing tells the operator when something running on the substrate stops.** INC-0007's egress
agent failed for a day, INC-0006's API was down until someone looked, and INC-0002's controller went
silent, each found by chance. This change deploys a health watcher on the Builder
(`deevnet.builder` [#44](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/44)), the
first of the options for INC-0007's action 4: the one that needs no new service or credential. How
an alert reaches the operator away from the Builder (a phone through ntfy, or mail) stays with the
[Observability](/docs/roadmap/infrastructure/substrate/observability/) item's operator-alerting waypoint.

Every five minutes, as the update watcher's read-only `deevnet-watch` account:

| Check | A problem when |
|---|---|
| Every substrate host, over SSH | it does not answer, or a systemd unit has failed |
| The Deevnet API, `/healthz` | it does not answer 200 |
| The Deevnet API, `/readyz` | its database is not `ok`. OpenBao sealed is normal ([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/)) |
| The Omada controller, `/api/info` | it does not answer, or is not `configured` |

A check that fails twice in a row is raised; it clears itself when it passes. What is raised shows in
a banner at login, from `/srv/health/notice`; `/srv/health/latest.txt` holds every check and
`events.log` a line for each problem raised or cleared. The watcher stays quiet for ten minutes after
the Builder boots.

**The health watcher has its own key.** On every host the read-only account gets a second line in
`authorized_keys`, pinned with `command=`, `restrict` and `from=` the Builder to
`deevnet-health-check`, which prints the failed units. The update watcher's key stays pinned to its
own check; neither key can run the other's.

## Goal

- Every substrate host answers the health watcher, and the API and controller checks pass.
- A unit failed on purpose raises the banner within two runs, and clearing it clears the banner.
- The update watcher still answers on every host.

## Scope

**In scope:** the health watcher and its timer, key and banner on the Builder; the health check and
the second key on every host the update watcher asks.
**Out of scope:** any notification off the Builder; the core router, the switch and the AP, which
have no account (the core router's health is implied by everything answering through it); the Pi
lab.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The update watcher's key stops working | every host | `authorized_keys` is rendered whole from the same values as before plus one line; Step 4 runs the update watcher's dry run |
| The health key runs more than its check | every host | `command=`, `restrict`, `from=`; Step 5 asks it for the update check and gets the health check |
| A noisy banner trains the operator to ignore it | the Builder | Two failed runs before a problem; known failures accepted per host in inventory, each with a reason |

## Prerequisites

- [ ] `deevnet.builder` #44 and this record merged

## Procedure

### Step 1: The watcher, and the check on the Builder VMs and hypervisors

**Run** (in `ansible-collection-deevnet.builder`):

```bash
make publish        # deevnet.builder at the user level, for deevnet.mgmt in Step 2
make health-watch
```

**Verify:** `systemctl list-timers deevnet-health-watch.timer` lists it; `/etc/deevnet/health-watch.pub`
holds an `ssh-ed25519` key; on `dv02bld001v01` and each hypervisor, the account's `authorized_keys`
has two lines.

### Step 2: The check on every service VM

**Run** (in `ansible-collection-deevnet.mgmt`):

```bash
make install-dev
ansible-playbook playbooks/site.yml --tags update_check
```

**Verify:** two lines in the account's `authorized_keys` on each service VM.

### Step 3: A dry run

**Run:** `make health-watch-dry-run`.

**Verify:** every host answers; the API and controller checks pass. Any unit already failed is
looked at: fixed, or accepted in inventory with a reason.

### Step 4: The update watcher still answers

**Run:** `make update-watch-dry-run`.

**Verify:** every host answers, as before.

### Step 5: Each key runs only its own check

On `dv02bld001v01`, from the Builder as `deevnet-watch`: the health key, asked for
`deevnet-update-check`, prints the health check's sections; the update key, asked for
`deevnet-health-check`, prints the update check's.

### Step 6: A problem raised and cleared

On `dv02bld001v01`: `sudo systemd-run --unit=deevnet-health-test /bin/false`, which leaves a failed
unit. Wait two runs.

**Verify:** a login on the Builder shows the banner naming `dv02bld001v01 unit deevnet-health-test.service`.
Then `sudo systemctl reset-failed deevnet-health-test.service`; after the next run the banner is gone
and `events.log` has the RAISED and CLEARED lines.

## Verification

The three points under Goal.

## Undo

On the Builder: `systemctl disable --now deevnet-health-watch.timer`, then remove its units,
`/usr/local/sbin/deevnet-health-watch`, `/etc/deevnet/health-watch.*`,
`/etc/profile.d/deevnet-health.sh`, `/srv/health` and the key `health_ed25519` in the account's
`.ssh`. Remove `/etc/deevnet/health-watch.pub` and run Steps 1 and 2 again: `authorized_keys` goes
back to one line. Then revert #44.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: the watcher and its timer on the Builder; the check on the Builder VMs and hypervisors
- [ ] Step 2: the check on every service VM
- [ ] Step 3: a dry run with every host answering, any failed unit dealt with
- [ ] Step 4: the update watcher answering on every host
- [ ] Step 5: each key runs only its own check
- [ ] Step 6: a failed unit raised the banner and its clearing cleared it
- [ ] The runbook says what the banner means and where to look
- [ ] INC-0007 action 4, INC-0006 action 4 and INC-0002 action 3 marked Done

## Outcome

Not yet run.
