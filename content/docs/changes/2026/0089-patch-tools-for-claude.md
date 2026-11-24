---
title: "CHG-0089: Patch Tools for Claude"
weight: -89
---

# CHG-0089: Patch Tools for Claude

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | **Planned** |
| **Window** | No outage. A quarter of an hour, operator at the Builder |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the update watcher, and the new MCP server) |
| **Automation** | `deevnet.builder`: role `patch_mcp`, `update_watch` extended; `make update-watch`, `make patch-mcp`, `make patch-mcp-register` |
| **Risk** | Low. Most likely to go wrong: the update watcher's new `latest.json` breaks its run, found by `make update-watch-now` in Step 1 |
| **Related changes** | [CHG-0082](/docs/changes/2026/0082-update-watcher/) and [CHG-0087](/docs/changes/2026/0087-update-scoreboard/), whose reports the tools read |
| **Related incidents** | None |
| **Related runbooks** | [Patching](/docs/runbook/substrate/lifecycle/patching/) |

---

## Summary

**Claude gets read-only tools for what needs patching: a Model Context Protocol (MCP) server on the
Builder, `deevnet-patch-mcp`, and a `patch-status` skill that ranks what the tools find and names the
change to open for each** (`deevnet.builder`
[#47](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/47)). Until now each answer
meant reading the update watcher's text report by hand.

The server runs only when Claude Code starts it, on the Builder, as the operator, over stdio. It reads
the files the update and health watchers already write, and nothing else: no tool runs a command,
opens a connection or writes, it listens on no port, and it holds no credential. Each tool declares
itself read-only.

| Tool | Answers |
|---|---|
| `patch_status` | per system: release and its end of life, counts of waiting updates (major, minor, security, Critical, Important); network releases; systems not answering; unacknowledged news |
| `host_updates` | one host's packages: installed and new version, class, advisories with severity |
| `security_advisories` | advisories at or above a severity, Critical first, with the hosts waiting on each |
| `os_releases` | each host's release and days to its end of life, flagged within 90 days |
| `health_status` | the health watcher's last run and what is raised |
| `discovery_report` | the newest discovery report |

For them, the update watcher also writes `/srv/updates/latest.json`, with each package's security
advisories and their severity, and each release's end of life from Fedora's published schedules. A
version that is one number alone (`less` 704 to 710) now counts as minor, so the service VMs no
longer show a false major update. The banner and its scoreboard are otherwise unchanged.

**The first case it must find is real:** the Builder runs Fedora 43, whose end of life Fedora's
schedule puts at 2026-12-09. The Builder's upgrade to Fedora 44 is the next change.

## Goal

- Every tool answers, from the live reports.
- Asked what needs patching, `patch-status` ranks the Builder's Fedora 43 end of life first.
- Nothing listens, and no tool writes.

## Prerequisites

- [ ] `deevnet.builder` #47 and this record merged

## Procedure

### Step 1: The watcher's data

**Run** (in `ansible-collection-deevnet.builder`):

```bash
make update-watch
make update-watch-now
```

**Verify:** `/srv/updates/latest.json` written; the banner's scoreboard shows no major update on the
service VMs.

### Step 2: The server

**Run:** `make patch-mcp`, then `make patch-mcp-test`.

**Verify:** six tools, all read-only; every call answers; an unknown host is refused.

### Step 3: Registered with Claude Code

**Run:** `make patch-mcp-register`.

**Verify:** `claude mcp list` shows `deevnet-patch` connected; `~/.claude/skills/patch-status` is
linked.

### Step 4: Used

In a new Claude Code session on the Builder: "what needs patching?"

**Verify:** `patch-status` answers from the tools, the Builder's Fedora 43 end of life first. While
the server runs, `ss -ltnp` shows it listening on nothing, and `/srv/updates` is unchanged.

## Undo

`claude mcp remove deevnet-patch --scope user`, remove the skill's link and
`/usr/local/bin/deevnet-patch-mcp`; revert #47 and run `make update-watch`.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: `latest.json` written, no false majors
- [ ] Step 2: every tool answers, read-only
- [ ] Step 3: registered, skill linked
- [ ] Step 4: `patch-status` ranks the Builder's Fedora 43 end of life first
- [ ] The Patching runbook says how to ask Claude

## Follow-ups

None.
