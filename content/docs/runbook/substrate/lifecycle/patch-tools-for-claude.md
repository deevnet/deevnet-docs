---
title: "Patch Tools for Claude"
weight: 6
---

# Patch Tools for Claude

**Claude answers what needs patching from read-only tools on the Builder: `deevnet-patch-mcp`, a
Model Context Protocol (MCP) server, and the `patch-status` skill built on it.** Asked "what needs
patching?" in a Claude Code session on the Builder, Claude reads the update and health watchers'
reports through the server, ranks what it finds, and names the change to open for each. Nothing it
does changes a system: applying a patch stays a change record the operator approves. Built by
[CHG-0089](/docs/changes/2026/0089-patch-tools-for-claude/).

## How it works

**The server runs only while Claude Code runs, on the Builder, as the operator, and only reads.**
Claude Code starts it and talks to it over stdio. It listens on no port, opens no connection, holds no
credential, and every tool declares itself read-only. What it reads:

| File | Written by | How often |
|---|---|---|
| `/srv/updates/latest.json` | the [update watcher](/docs/runbook/substrate/lifecycle/patching/#updates-waiting): every host's waiting packages, whether each is major or minor, the security advisories it fixes with their severity, and each OS release's end of life | daily |
| `/srv/health/` | the [health watcher](/docs/runbook/substrate/recovery/health-watcher/) | every five minutes |
| `/srv/discovery/<date>.json` | `make discover` (`deevnet.mgmt`) | when run |

Every answer carries `checked_at`, the time of the update watcher's last run: the tools are as fresh
as it is.

## The tools

| Tool | Answers |
|---|---|
| `patch_status` | per system: its OS release and days to end of life, and counts of waiting updates (major, minor, security, Critical, Important); newer releases for the core router and network devices; systems that did not answer; news not yet acknowledged |
| `host_updates(host, only)` | one host's packages, installed and new version, class, and advisories with severity; `only` is `all`, `major`, `security` or `critical` |
| `security_advisories(min_severity)` | each advisory at or above a severity, Critical first, with the hosts waiting on it. The hypervisors' Debian security updates carry no advisory id or severity, and are listed as unrated |
| `os_releases` | each host's release and end-of-life date, flagged within 90 days or past it |
| `health_status` | the health watcher's last run and what it has raised |
| `discovery_report` | the newest discovery report: versions on every system, including the core router, switch and AP |

**Major** is a change in the first part of the version (kernel 6.17 to 7.3); a version that is a date
or one number alone (linux-firmware, `less`) counts as minor.

## Asking

**In a Claude Code session on the Builder, ask in plain words:** "what needs patching?", "anything
critical waiting?", "when does the Builder's Fedora go out of support?". The `patch-status` skill
answers most urgent first:

1. a release past or within 90 days of end of life;
2. Critical, then Important, security advisories;
3. systems that did not answer;
4. newer releases for the core router and network devices;
5. the routine backlog.

For each it names the change to open: a release upgrade, a patch change one host at a time with a
snapshot first, a hypervisor change, or the
[Core Router Patch](/docs/runbook/substrate/lifecycle/core-router-patch/) runbook.

**After patching, refresh before asking again:** `make update-watch-now` in
`ansible-collection-deevnet.builder`, or the answer is still the morning's.

## Setting it up

In `ansible-collection-deevnet.builder`, on the Builder:

```bash
make patch-mcp            # install the server and the MCP Python SDK (python3-mcp, from Fedora)
make patch-mcp-test       # start it, call every tool through the SDK's client, report each
make patch-mcp-register   # add it to Claude Code (user scope) and link the skills
```

`make patch-mcp-register` is once per operator account. It registers at user scope because
`/srv/dvnt`, where Claude Code runs, is the organization's `.github` checkout. The skills are linked
from the collection's checkout, so they follow its branch. Claude Code loads MCP servers when a
session starts: after registering, start a new session.

## When it goes wrong

| Symptom | Check |
|---|---|
| Claude has no `deevnet-patch` tools | `claude mcp list` shows `deevnet-patch` connected; if absent, `make patch-mcp-register` and a new session |
| "no update report" | `/srv/updates/latest.json` is missing: `make update-watch-now` |
| An answer looks old | its `checked_at`; `make update-watch-now` |
| A release shows "no end-of-life date recorded" | add it to `update_watch_eol` in the `update_watch` role's defaults, from the vendor's published schedule, then `make update-watch` and `make update-watch-now` |
| A host "did not answer" | the update watcher could not ask it: [Troubleshoot a Service VM](/docs/runbook/substrate/recovery/service-vm-troubleshooting/), and `health_status` |

The end-of-life dates are the vendors', recorded in `update_watch_eol` with where each came from.
Fedora marks its dates as changeable: recheck them when a Fedora release ships.
