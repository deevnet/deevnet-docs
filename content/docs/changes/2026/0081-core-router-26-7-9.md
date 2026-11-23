---
title: "CHG-0081: The Core Router Updated to OPNsense 26.7.9_3"
weight: -81
---

# CHG-0081: The Core Router Updated to OPNsense 26.7.9_3

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Change type** | Upgrade |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-22**; recorded after the fact on 2026-11-23 |
| **Window** | Not recorded |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` |
| **Automation** | None: applied by hand through OPNsense's web interface |
| **Risk** | Not assessed beforehand |
| **Related changes** | None |
| **Related incidents** | None |
| **Related runbooks** | [Core Router Patch](/docs/runbook/substrate/lifecycle/core-router-patch/), written because of this change |

---

## Summary

**This record was written after the change, from what the site shows, because none was opened
before it.** On 2026-11-22 the operator updated the core router from OPNsense 26.7.3_11 to 26.7.9_3,
within the 26.7 line, through the web interface's firmware updates. The first discovery report, on
2026-11-23, found the router on 26.7.9_3 while the Software Catalog still listed 26.7.3_11, and the
operator confirmed the update.

The steps a patch takes around the update itself were missed: no record, no release notes read
into one, no configuration backup taken around it. They are now the
[Core Router Patch](/docs/runbook/substrate/lifecycle/core-router-patch/) procedure, so the next
patch follows them.

## Goal

The router on the latest 26.7 point release.

## Scope

**In scope:** OPNsense and the packages its firmware update brought with it.
**Out of scope:** any change to the router's configuration.

## Risk and impact

Not assessed before the change. Nothing has been reported since that points to it: on 2026-11-23
the router answered its API, and every system behind it that discovery reads answered too.

## Procedure

Not recorded. The update was applied from the web interface's firmware page.

## Verification

From the discovery report of 2026-11-23 (`make discover`, kept on the Builder):

| Item | Before (Software Catalog) | After (observed 2026-11-23) |
|---|---|---|
| OPNsense | 26.7.3_11 | 26.7.9_3 |
| FreeBSD base | not recorded | 15 (from the package mirror's ABI); OPNsense base set 26.7.9 |
| Kea | not recorded | 3.0.4 |
| Unbound | not recorded | 1.26.2 |

## Undo

A point update is undone forward. The way back to 26.7.3_11 would be a reinstall and a restored
configuration. The inventory's backup of 2026-11-15 serves: `make backup-router` on 2026-11-23 found
the configuration unchanged from it, so it holds the configuration from both before and after the
update.

## To close

**This change closes when every item below is done.**

- [x] The update applied
- [x] The new version read and confirmed: discovery report, 2026-11-23
- [x] The Software Catalog lists 26.7.9_3
- [x] The Core Router Patch procedure written, so the next patch has one

## Outcome

**The router runs OPNsense 26.7.9_3, and the practice for its next patch is written down.** The
change itself was routine and caused no reported fault; what it lacked was the record, the release
notes and the backups around it.

### Departures from the plan

There was no plan: the change was made before a record existed.

## Follow-ups

- [x] Run `make backup-router`, so the inventory holds 26.7.9's configuration: run 2026-11-23, unchanged from the backup of 2026-11-15, so nothing to commit
