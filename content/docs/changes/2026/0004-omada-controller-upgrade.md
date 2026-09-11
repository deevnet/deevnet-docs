---
title: "CHG-0004: Omada Controller Upgrade"
weight: 4
aliases:
  - /docs/changes/2026/0004-omada-controller-and-network-firmware/
---

# CHG-0004: Omada Controller Upgrade

| | |
|---|---|
| **Date** | 2026-09-10 |
| **Change type** | Upgrade |
| **Classification** | Structural — a controller outage, but nothing on site depended on the controller |
| **Status** | **Complete** 2026-09-10. Re-scoped 2026-09-11: see [Scope change](#scope-change). |
| **Window** | 2026-09-10, 05:16–05:30 local |
| **Site** | mobile |
| **Systems** | Omada controller on `dv00bld001p01` |
| **Automation** | Controller pinned by inventory #24 and builder #13; runbook in docs #30 |
| **Risk** | A newer controller's database cannot be opened by an older one |
| **Related changes** | [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) (the AP) and [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/) (the switch), both split out of this record |
| **Related incidents** | None |
| **Related runbooks** | [Omada Controller Upgrade](/docs/runbook/lifecycle/omada-controller-upgrade/); [Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/) |

---

## Summary

The Omada controller ran 6.1. This change upgraded it in place to 6.3.0.45, the current
release, and staged 6.2.14.11 as a rehearsed fallback. The aim was to bring the controller current
before it is used to manage the site's Omada devices. The switch's current firmware recommends
controller 6.2.0.

## Scope change

This record opened as *Omada Controller and Network Firmware Upgrade*, with three phases: the
controller, the switch's firmware and the AP's firmware.

On 2026-09-11 it was split, so that the AP could be fixed without touching the switch:

| Was | Now |
|---|---|
| Phase 1 — controller | This record, complete |
| Phase 3 — AP firmware | [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/), which also adopts the AP and has the controller provision its SSIDs |
| Phase 2 — switch firmware | [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/), a future change |

The phases' plans, baselines, risks and undo moved to those records intact.

## Goal

- The controller runs **6.3.0.45**, with its data intact and the `a_autoprov` automation login
  working.
- **6.2.14.11** is staged and rehearsed as the fallback, and the pre-upgrade data snapshot is
  kept.
- Inventory pins the controller build.

## Scope

**In scope:** the controller. **Out of scope:** device firmware, and adoption — see
[Scope change](#scope-change).

## Risk and impact

| Risk | Guard |
|---|---|
| A newer controller's database cannot be opened by an older one | A clean snapshot was taken first; 6.2.14.11 was rehearsed on a copy of it |
| The controller upgrades device firmware on its own | `autoUpgrade` is off at site level (checked 2026-09-10) |

---

## Procedure

Followed [Omada Controller Upgrade](/docs/runbook/lifecycle/omada-controller-upgrade/): stage the
image while the controller runs; stop it cleanly; snapshot the data; recreate the container on
the new image; verify; pin inventory. Then 6.2.14.11 was staged as the fallback and rehearsed.

## Verification

The same `omadacId` and `configured: true` after the upgrade; `Database upgraded` in the server
log; `a_autoprov` logging in over the API and listing the site.

## Undo

[Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/): restore the
pre-upgrade snapshot, and start it on 6.2.14.11, or on 6.1 as the last resort. Anything
configured on 6.3 since the snapshot is lost.

---

## Outcome

Times are local, from file, log and commit timestamps.

| Time | What happened |
|---|---|
| 05:16 | 6.3.0.45 pulled while 6.1.0.19 kept running, and saved to the artifact server |
| 05:17 | Controller stopped. `mongod.log` ended with `mongod shutdown complete`. Data snapshot taken, 138 MB, with its sha256 recorded alongside. |
| 05:18 | Container recreated on 6.3.0.45. `Upgrading the database` at 05:18:54, `Database upgraded` a second later, `Omada Network Application started` at 05:18:59. |
| shortly after | Verified: the same `omadacId`, still `configured`; `a_autoprov` logged in over the API and listed the `dvntm` site |
| 05:26 | 6.2.14.11 pulled and saved as the fallback |
| 05:27–05:30 | Fallback rehearsed. 6.2.14.11 was started on a copy of the snapshot, in an isolated container on a loopback-only port. It upgraded the database in under a minute, kept the site, and the automation login worked. The rehearsal was then removed. |
| 05:30–05:44 | Inventory pinned to 6.3.0.45, with 6.2 and 6.1 declared as fallbacks (inventory #24); role default set (builder #13); runbook written (docs #30) |

The controller was down for about two minutes. No device was adopted, so nothing on site
depended on it being up.

**Found along the way:** the controller had never adopted the switch. The AP had been pending
since 2026-03-24, when it was forgotten with a configuration reset.

## Follow-ups

- [x] **Decided who owns network device configuration:** inventory owns it, and the controller
  applies it through its Open API — [ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/).
- [ ] **Fix or retire `playbooks/upgrade-omada.yml`** in the builder collection. It hard-codes a
  fresh install and deletes the controller's data.
