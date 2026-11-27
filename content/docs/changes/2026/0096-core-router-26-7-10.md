---
title: "CHG-0096: The Core Router Updated to OPNsense 26.7.10"
weight: -96
---

# CHG-0096: The Core Router Updated to OPNsense 26.7.10

| | |
|---|---|
| **Date** | 2026-11-27 |
| **Change type** | Upgrade |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-27**; recorded after the fact the same day |
| **Window** | Not recorded. Between the discovery reports of 2026-11-26 16:47 and 2026-11-27 05:11 EST; the router's firmware last ran at 04:25 EST (09:25 UTC) |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` |
| **Automation** | None: applied by hand through OPNsense's web interface |
| **Risk** | Not assessed beforehand |
| **Related changes** | [CHG-0081](/docs/changes/2026/0081-core-router-26-7-9/), the last update recorded after the fact; [CHG-0094](/docs/changes/2026/0094-patch-builder-service-vms/) and [CHG-0095](/docs/changes/2026/0095-hypervisors-proxmox-9-3/), the patch cycle it belongs to |
| **Related incidents** | None |
| **Related runbooks** | [Core Router Patch](/docs/runbook/substrate/lifecycle/core-router-patch/) |

---

## Summary

**This record was written after the change, from what the site shows, because none was opened
before it.** Overnight, while CHG-0094 was patching the service VMs and the Builder, the operator
updated the core router from OPNsense 26.7.9_3 to 26.7.10, within the 26.7 line, through the web
interface's firmware page. The discovery report of 2026-11-27 05:11 found the router on 26.7.10;
the operator confirmed the update.

**The update was click-operated because OPNsense offers no other way Deevnet uses yet.** Its
firmware API can run the same update, but the one privilege that allows it ("System: Firmware")
also allows every other firmware action; automating it is its own piece of work, to be scoped
separately.

## Goal

The router on the latest 26.7 point release.

## Scope

**In scope:** OPNsense and the packages its firmware update brought with it.
**Out of scope:** any change to the router's configuration.

## Risk and impact

Not assessed before the change. **The health watcher's 04:30 run had one check failing**, five
minutes after the router's firmware ran: consistent with the update's restart, though the watcher
does not log which check failed. It was not raised (a check is a problem after two failed runs in a
row), and the next run passed. Its other failing run, at 05:00, matches `dv02bld001v01`'s reboot
under CHG-0094. Every other run since 04:00 had all 14 checks passing, the update watcher read
every host through the router, and CHG-0095's downloads crossed it at 1.2 MB/s with no ping missed.

## Procedure

Not recorded. The update was applied from the web interface's firmware page.

## Verification

From the discovery reports (`make discover`, kept on the Builder in `/srv/discovery`):

| Item | Before (2026-11-26 16:47) | After (2026-11-27 05:11) |
|---|---|---|
| OPNsense | 26.7.9_3 | 26.7.10 |
| FreeBSD base | 15 | 15 |
| Kea DHCPv4 | 3.0.4 | 3.0.5 |
| Unbound | 1.26.2 | 1.26.2 |
| `os-isc-dhcp`, `os-wol` | 1.0_7, 2.5_4 | unchanged |

The router reports no reboot pending (`needs_reboot` 0), and 26.7.10 as the latest release it knows.

## Undo

A point update is undone forward. The way back to 26.7.9_3 would be a reinstall and a restored
configuration from the inventory's router backup.

## To close

**This change closes when every item below is done.**

- [x] The update applied
- [x] The new version read and confirmed: discovery report, 2026-11-27 05:11
- [x] The Software Catalog lists 26.7.10

## Outcome

**The router runs OPNsense 26.7.10, and the update watcher shows nothing waiting anywhere on the
substrate.** As with CHG-0081, the change caused no reported fault; what it lacked was the record,
the release notes and the backups around it.

### Departures from the plan

There was no plan: the change was made before a record existed.

## Follow-ups

- [ ] The health watcher logs which check failed, not only how many, so a blip like 04:30's can be read afterwards
- [ ] Run `make backup-router` (operator), so the inventory holds 26.7.10's configuration
- [ ] Scope automating the router's update through OPNsense's firmware API, and with it which key may hold "System: Firmware": discovery's `GET core/firmware/info` works with the key every `deevnet.net` role uses, so that key already holds it
