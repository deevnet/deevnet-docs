---
title: "The Health Banner"
weight: 0
---

# The Health Banner

What the health banner on the Builder says, and what to do about it. **Every five minutes the
health watcher on the Builder checks that the substrate is running, and a check that fails twice in
a row shows in a banner at every login on the Builder until it passes again.** It is the substrate's
only alerting today: nothing reaches the operator away from the Builder.

```text
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
Deevnet health: 1 problem
  dv02col001v01 unit deevnet-health-test.service: failed (since 2026-11-24 05:20 EST)
Details: /srv/health/latest.txt. This clears itself when the check passes.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

## What it checks

| Check | A problem when | Where to start |
|---|---|---|
| `<host> answers` | a substrate service VM, Builder VM or hypervisor does not answer over SSH | the host's console; [Troubleshoot a Service VM](/docs/runbook/substrate/recovery/service-vm-troubleshooting/) |
| `<host> unit <unit>` | a systemd unit on that host has failed | `systemctl status <unit>` and `journalctl -u <unit>` on the host |
| `Deevnet API alive` | the API's `/healthz` does not answer 200 | the API's container on `dv02prv001v01` |
| `Deevnet API database` | the API's `/readyz` says its database is not `ok` | PostgreSQL on `dv02prv001v01` |
| `Omada controller configured` | the controller's `/api/info` does not answer, or says it is not configured | [Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/) |
| `<hypervisor> VM hardware report` | the hypervisor's report of its VMs' hardware is missing, unreadable or over 30 minutes old | `systemctl status deevnet-vm-hardware.timer deevnet-vm-hardware.service` on the hypervisor |
| `<hypervisor> VM <vmid> <name> on the hardware profile` | the VM differs from the [VM hardware profile](/docs/architecture/decisions/substrate/0046-vm-hardware-profile/) where inventory declares no exception; the detail names each difference | `make vm-profile` in `deevnet.mgmt`; moving a VM is a change record, as in [CHG-0100](/docs/changes/2026/0100-tenant-vms-vm-profile/) |

**OpenBao sealed is not a problem.** Outside a work session the API's `/readyz` answers 503 with
OpenBao sealed, as [ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/)
intends; the watcher reads only its database.

**The core router, the switch and the AP are not checked directly.** Everything else answers
through them, so they show as every host not answering at once.

A host that does not answer keeps the unit problems it had: nothing is known about them until it
answers again.

## Where to look

On the Builder, in `/srv/health`:

- `latest.txt`: every check and its result, from the last run.
- `events.log`: one line each time a problem is raised or cleared.
- `notice`: what the banner shows. Empty when nothing is wrong.

From `ansible-collection-deevnet.builder`:

```bash
make health-watch-now       # run it now and show latest.txt
make health-watch-dry-run   # check everything, change nothing
```

## Quiet times

**The watcher does not run for ten minutes after the Builder boots**, while the hypervisors and
their VMs come up ([Shutdown and Power-On](/docs/runbook/substrate/lifecycle/shutdown-and-power-on/)).

**A unit that is known to fail and accepted** is listed in inventory, in
`health_watch_ignore_units` for the Builder (`{host: [unit, ...]}`), each with its reason beside it,
and deployed with `make health-watch`. Fixing it is better.

## How it asks

**The watcher uses the update watcher's read-only account, `deevnet-watch`, and its one key.** On
each host that key runs one program, `deevnet-watch-check`, which answers `health` (the failed units)
and `updates` (waiting updates) and refuses anything else
([Security Controls](/docs/policies/risk-management/security-controls/#credentials)). The API and the
controller are asked over HTTPS from the Builder. Built by
[CHG-0086](/docs/changes/2026/0086-health-watcher/).
