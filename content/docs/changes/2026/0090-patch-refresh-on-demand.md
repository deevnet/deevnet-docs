---
title: "CHG-0090: A Fresh Patch Scan on Demand"
weight: -90
---

# CHG-0090: A Fresh Patch Scan on Demand

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-24** |
| **Window** | No outage. A quarter of an hour, operator at the Builder |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the patch MCP server and a polkit rule) |
| **Automation** | `deevnet.builder`: role `patch_mcp`; `make patch-mcp`, `make patch-mcp-test-refresh` |
| **Risk** | Low. Most likely to go wrong: the polkit rule allows more than starting the one unit, checked in Step 2 by trying to stop it |
| **Related changes** | [CHG-0089](/docs/changes/2026/0089-patch-tools-for-claude/), which built the server; [CHG-0082](/docs/changes/2026/0082-update-watcher/), the update watcher it runs |
| **Related incidents** | None |
| **Related runbooks** | [Patch Tools for Claude](/docs/runbook/substrate/lifecycle/patch-tools-for-claude/) |

---

## Summary

**The patch MCP server gets a seventh tool, `refresh_updates`, which runs the update watcher now and
answers from the fresh report** (`deevnet.builder`
[#50](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/50)). Until now Claude
answered from the watcher's morning run, and a fresh look meant the operator running
`make update-watch-now` first.

`refresh_updates` starts the watcher's own systemd unit and waits for it, about half a minute. The watcher
runs as it does from its timer: as `deevnet-watch`, asking each host with that account's
forced-command key. The server never holds that key, still holds no credential and listens on no port,
and no tool changes a system. What changes is that one tool now causes writes, the watcher's own
reports in `/srv/updates` and its banner, so it is declared not read-only; the other six stay
read-only.

The server runs as the operator and has no terminal to type a password into. A polkit rule lets the
`wheel` group start `deevnet-update-watch.service`, and do nothing else to it or any other unit,
without one. Members of `wheel` can already start it with sudo.

The `patch-status` skill refreshes first when asked for a fresh look, after patching, or when the
data is over a day old.

## Goal

- `refresh_updates` runs the update watcher and answers from the new report.
- The operator can start the unit without a password, and cannot stop or restart it, or start
  another, without one.
- The other six tools are unchanged and read-only.

## Prerequisites

- [x] `deevnet.builder` #50 and this record merged

## Procedure

### Step 1: Deploy

**Run** (in `ansible-collection-deevnet.builder`): `make patch-mcp`.

**Verify:** `/etc/polkit-1/rules.d/50-deevnet-patch-refresh.rules` installed; the server lists seven
tools.

### Step 2: The rule's limits

**Run**, as the operator, without sudo:

```bash
systemctl start --no-ask-password deevnet-update-watch.service
systemctl restart --no-ask-password deevnet-update-watch.service
systemctl start --no-ask-password deevnet-health-watch.service
```

**Verify:** the first succeeds; the other two are refused ("Interactive authentication required").

### Step 3: A refresh through the server

**Run:** `make patch-mcp-test-refresh`.

**Verify:** every tool answers, `refresh_updates` last with a new `checked_at`; only `refresh_updates`
is listed as not read-only.

### Step 4: Used

In a new Claude Code session on the Builder: "what needs patching? take a fresh look".

**Verify:** `patch-status` calls `refresh_updates` first and answers from the new `checked_at`.

## Undo

Revert #50 and run `make patch-mcp`, then remove
`/etc/polkit-1/rules.d/50-deevnet-patch-refresh.rules`.

## To close

**This change closes when every item below is done.**

- [x] Step 1: deployed, seven tools
- [x] Step 2: the rule allows starting the update watcher and nothing else
- [x] Step 3: `refresh_updates` answers from a fresh report
- [x] Step 4: `patch-status` refreshes when asked for a fresh look
- [x] The runbook says the server can refresh: [Patch Tools for Claude](/docs/runbook/substrate/lifecycle/patch-tools-for-claude/)

## Outcome

**Deployed and used; `refresh_updates` runs the update watcher and answers from the new report.** All commands
ran from the Builder.

| When | Steps | What happened |
|---|---|---|
| 16:52 | Step 1 | `make patch-mcp`: two changes, the server and the polkit rule. No failure |
| 16:53 | Step 2 | As the operator, sudo's cached credential cleared first: starting `deevnet-update-watch.service` succeeded; restarting or stopping it, and starting `deevnet-health-watch.service`, were refused ("requires interactive authentication") |
| 16:53 | Step 3 | `make patch-mcp-test-refresh`: seven tools, six read-only, `refresh_updates` not; every call answered; `refresh_updates` moved `checked_at` from 21:53:13Z to 21:53:40Z, 25 seconds in all |
| 17:05 | Step 4 | A new Claude Code session, asked "what needs patching? take a fresh look": `patch-status` called `refresh_updates` first, which moved `checked_at` from 21:53:40Z to 22:05:12Z, and answered from it, the Builder's Fedora 43 end of life first. Asked the same without "fresh", it answered from the existing report without refreshing |

A fresh scan asks every host again, but each answers from its own package metadata, 0.5 to 1.1
days old at the time: an update published within the last hours shows at the hosts' next metadata
refresh, not sooner. Making hosts refresh their metadata on each scan would download package
metadata across the core router on every call, so the scan leaves it to them.

## Follow-ups

None.
