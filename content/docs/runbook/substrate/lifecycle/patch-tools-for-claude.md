---
title: "Patch Tools for Claude"
weight: 6
---

# Patch Tools for Claude

**Claude answers what needs patching from tools on the Builder: `deevnet-patch-mcp`, a Model
Context Protocol (MCP) server, and the `patch-status` skill built on it.** Asked "what needs
patching?" in a Claude Code session on the Builder, Claude reads the update and health watchers'
reports through the server, running a fresh scan first when the report is old or asked to, ranks
what it finds, and names the change to open for each. Nothing it does changes a system: applying a
patch stays a change record the operator approves. Built by
[CHG-0089](/docs/changes/2026/0089-patch-tools-for-claude/); the fresh scan by
[CHG-0090](/docs/changes/2026/0090-patch-refresh-on-demand/).

## How it works

**The server runs only while Claude Code runs, on the Builder, as the operator.** Claude Code starts
it and talks to it over stdio. It listens on no port and holds no credential. Six of its tools only
read; the seventh, `refresh_updates`, starts the update watcher, which asks every host with its own
key and rewrites its reports. What it reads:

| File | Written by | How often |
|---|---|---|
| `/srv/updates/latest.json` | the [update watcher](/docs/runbook/substrate/lifecycle/patching/#updates-waiting): every host's waiting packages, whether each is major or minor, the security advisories it fixes with their severity, and each OS release's end of life | daily |
| `/srv/health/` | the [health watcher](/docs/runbook/substrate/recovery/health-watcher/) | every five minutes |
| `/srv/discovery/<date>.json` | `make discover` (`deevnet.mgmt`) | when run |

Every answer carries `checked_at`, the time of the update watcher's last run: the tools are as fresh
as it is.

**A fresh scan.** `refresh_updates` runs `systemctl start deevnet-update-watch.service`, the
watcher's own unit, exactly as its daily timer does, and waits for it: about half a minute. The
operator may start that unit without a password through a polkit rule,
`/etc/polkit-1/rules.d/50-deevnet-patch-refresh.rules`, which allows the `wheel` group to start it
and nothing else: stopping or restarting it, or starting any other unit, still needs authentication.
The tool is declared not read-only, since the watcher writes its reports and the banner, and safe to
repeat. Each host answers from its own package metadata, which it refreshes on its own schedule:
an update published within the last hours may not show until then.

## The tools

| Tool | Answers |
|---|---|
| `patch_status` | per system: its OS release and days to end of life, and counts of waiting updates (major, minor, security, Critical, Important); newer releases for the core router and network devices; systems that did not answer; news not yet acknowledged |
| `host_updates(host, only)` | one host's packages, installed and new version, class, and advisories with severity; `only` is `all`, `major`, `security` or `critical` |
| `security_advisories(min_severity)` | each advisory at or above a severity, Critical first, with the hosts waiting on it. The hypervisors' Debian security updates carry no advisory id or severity, and are listed as unrated |
| `os_releases` | each host's release and end-of-life date, flagged within 90 days or past it |
| `health_status` | the health watcher's last run and what it has raised |
| `discovery_report` | the newest discovery report: versions on every system, including the core router, switch and AP |
| `refresh_updates` | runs the update watcher now, then answers as `patch_status` does from the new report, with the previous `checked_at` |

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

**For the latest, ask for a fresh look:** "what needs patching? take a fresh look". The skill
refreshes by itself after patching or when the report is more than a day old; otherwise it answers
from the morning's run, without the half-minute wait.

## Setting it up

In `ansible-collection-deevnet.builder`, on the Builder:

```bash
make patch-mcp                # install the server, its polkit rule and the MCP Python SDK (python3-mcp, from Fedora)
make patch-mcp-test           # start it, call every read-only tool through the SDK's client, report each
make patch-mcp-test-refresh   # the same, then a fresh scan through refresh_updates
make patch-mcp-register       # add it to Claude Code (user scope) and link the skills
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
| An answer looks old | its `checked_at`; ask for a fresh look, or `make update-watch-now` |
| `refresh_updates` fails with "interactive authentication" | the polkit rule is missing, or the operator is not in `wheel`: `make patch-mcp` |
| A release shows "no end-of-life date recorded" | add it to `update_watch_eol` in the `update_watch` role's defaults, from the vendor's published schedule, then `make update-watch` and `make update-watch-now` |
| A host "did not answer" | the update watcher could not ask it: [Troubleshoot a Service VM](/docs/runbook/substrate/recovery/service-vm-troubleshooting/), and `health_status` |

The end-of-life dates are the vendors', recorded in `update_watch_eol` with where each came from.
Fedora marks its dates as changeable: recheck them when a Fedora release ships.
