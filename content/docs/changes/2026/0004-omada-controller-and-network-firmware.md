---
title: "CHG-0004: Omada Controller and Network Firmware Upgrade"
weight: 4
---

# CHG-0004: Omada Controller and Network Firmware Upgrade

| | |
|---|---|
| **Date** | 2026-09-10 |
| **Change type** | Upgrade |
| **Classification** | Disruptive — phase 2 reboots the switch that carries every wired path on site |
| **Status** | **In progress.** Phase 1 (controller) complete 2026-09-10. Phases 2 (switch) and 3 (AP) planned, not yet scheduled. |
| **Window** | Phase 1: 2026-09-10, 05:16–05:30 local. Phases 2–3: to be scheduled, with the operator on site and a console cable to hand. |
| **Site** | mobile |
| **Systems** | Omada controller on `dv00bld001p01`; access switch `dv02acc001p01` (SG2218, hardware 1.20); AP `dv02wap001p01` (EAP650-Outdoor v1) |
| **Automation** | Firmware mirrored by inventory #22 and #23; controller pinned by inventory #24 and builder #13; procedures in docs #28, #29 and #30 |
| **Risk** | High. The switch reboot takes the builder, the controller and Ansible offline with everything else, and the AP's 1.3.3 hop cannot be undone. |
| **Related changes** | [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) — its SSID workaround exists because of the AP's old firmware |
| **Related incidents** | None |
| **Related runbooks** | [Omada Controller Upgrade](/docs/runbook/lifecycle/omada-controller-upgrade/); [Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/); [Access Switch → Firmware upgrade](/docs/runbook/recovery/console-recovery/access-switch/#firmware-upgrade); [Wireless AP → step 4](/docs/runbook/recovery/console-recovery/wireless-ap/#4-upgrade-the-firmware-before-adopting) |

---

## Summary

The mobile site's Omada controller and both Omada devices were well behind current.

- **The AP** runs 1.0.4 (April 2023). Omada 6.1 could not push VLAN-tagged SSIDs to it, which
  is why [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) left the SSIDs configured on
  the AP by hand.
- **The switch** runs 1.20.1 (January 2024), eight builds behind.
- **The controller** ran 6.1. The switch's current firmware recommends controller 6.2.0.

This change brings all three current before Omada is used to manage the devices. Adopting them
is a separate change: adopting the switch hands its configuration to the controller, and who
owns that configuration — Ansible or the controller — is not yet decided.

## Goal

The end state that counts as done:

- The controller runs **6.3.0.45**, with its data intact and the `a_autoprov` automation login
  working. **6.2.14.11** is staged and rehearsed as the fallback, with the pre-upgrade data
  snapshot kept. *Done.*
- The switch runs **1.20.24** in one image slot, with **1.20.1** kept in the other as the
  rollback. Its configuration is unchanged, Ansible still connects, and STP and LLDP are in a
  state that was chosen rather than inherited from new defaults.
- The AP runs **1.3.11**, reached through 1.2.5 and 1.3.3, and every SSID still tags onto its
  VLAN.
- Inventory pins the controller build and each firmware file by sha256.

## Scope

**In scope:** the controller upgrade, and the switch and AP firmware upgrades.
**Out of scope:** adopting the switch or the AP into Omada, moving the SSIDs to controller
provisioning, and the home site.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A newer controller's database cannot be opened by an older one | Phase 1 | A clean snapshot was taken first; 6.2.14.11 was rehearsed on a copy of it |
| The switch reboot drops every wired path, the builder's included — the controller, Ansible and the browser used for the upload | Phase 2 | Upload without auto-reboot, so the outage starts when the operator chooses; console cable to hand; the hypervisors are not clustered, so nothing fences |
| Automation loses the switch: it is reached over legacy SSH key exchange, and 1.20.4 (OpenSSL) and 1.20.19 (SSH fix) are where that could change | Phase 2 | Verification leads with "does Ansible connect"; 1.20.1 stays on flash as the rollback |
| New defaults come up under an unchanged config: STP is on by default from 1.20.9, LLDP from 1.20.4 | Phase 2 | Baseline recorded below: both **disabled** today |
| Each AP build declares a minimum prior version | Phase 3 | Hops in order, confirming the version between each |
| The AP's 1.3.3 hop is irreversible — TP-Link state a downgrade needs their support | Phase 3 | Done last, after the switch is proven; all three files mirrored in advance |
| An in-place hop loses the AP's standalone SSID configuration | Phase 3 | Fall back to the reset-and-recover path in [Wireless AP](/docs/runbook/recovery/console-recovery/wireless-ap/) |
| The controller upgrades device firmware on its own once devices are adopted | Later | `autoUpgrade` is off at site level (checked 2026-09-10) |

## Prerequisites

For phases 2 and 3:

- [x] Firmware mirrored and pinned: switch 1.20.24; AP 1.2.5, 1.3.3 and 1.3.11. All four files
  matched their pinned sha256 on 2026-09-10.
- [x] Controller on 6.3 (phase 1).
- [ ] Operator on site, with a console cable to the switch.
- [ ] Vault decrypted, so Ansible can verify the switch before and after.
- [ ] The switch's `show system-info`, `show image-info` and `running-config` captured on the day,
  per the procedure's step 1.

### Baseline, 2026-09-10

Read-only, from the switch and the controller:

| | |
|---|---|
| Switch firmware | `1.20.1 Build 20240115` in `image2.bin` (boots); `image1.bin` holds the factory `1.1.3` |
| Switch STP | `Spanning tree is disabled` |
| Switch LLDP | `LLDP Status: Disabled` |
| AP | `1.0.4 Build 20230421`; answers at `10.20.99.9`; pending in the controller, not adopted |
| Controller | `6.3.0.45`; site `autoUpgrade` disabled; the switch is not adopted |

---

## Procedure

Phases run in order. The switch goes first because its rollback sits on its own flash; the AP's
irreversible hop waits until the switch is proven. The AP work runs over the switch, so both
belong in the same window.

### Phase 1 — Controller 6.1.0.19 → 6.3.0.45 · *Complete*

Followed [Omada Controller Upgrade](/docs/runbook/lifecycle/omada-controller-upgrade/):
stage the image while the controller runs; stop it cleanly; snapshot the data; recreate the
container on the new image; verify; pin inventory. Then 6.2.14.11 was staged as the fallback
and rehearsed. See [Outcome](#outcome).

### Phase 2 — Switch 1.20.1 → 1.20.24 · *Planned*

Follow [Access Switch → Firmware upgrade](/docs/runbook/recovery/console-recovery/access-switch/#firmware-upgrade):

1. **Record where it starts** — capture system info, image info and the running config.
2. **Upload into the backup image** from `https://10.20.99.10` — the `.bin`, with the auto-reboot
   box **unchecked**.
3. **Boot from it** — set the next startup image, then reboot at a moment of the operator's
   choosing.
4. **Verify** — version and image slots; Ansible connects; STP and LLDP compared with the
   baseline above; the running config compared with step 1; the reachability pings; one run of
   `switch-vlans.yml`.

**Undo:** [Undo phase 2](#undo-phase-2)

### Phase 3 — AP 1.0.4 → 1.2.5 → 1.3.3 → 1.3.11 · *Planned*

**In place**, through the AP's own web UI at `https://10.20.99.9`, reached from the builder on
the management segment. There is no factory reset first; the aim is that the standalone SSIDs
keep their configuration and serve between hops. The file handling and version checks follow
[Wireless AP → step 4](/docs/runbook/recovery/console-recovery/wireless-ap/#4-upgrade-the-firmware-before-adopting),
which describes the same upload for an AP that has been reset.

For each hop, in order — `1.2.5`, `1.3.3`, `1.3.11`:

1. Download the hop's `.bin` (not the `.zip`) from
   `http://artifacts.mobile.deevnet.net/firmware/eap650-outdoor/` to the machine running the
   browser.
2. Upload it under **System → Firmware Update**. The AP reboots; wireless is down until it is
   back.
3. Confirm **Status → Device Information → Firmware Version** shows the hop's version before
   starting the next.

After the last hop, check each SSID from a client, as
[CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/port-migration/#step-13-ap-ssid-configuration)
did: `DVNTM` → `10.20.10.x`, `DVNTM-IOT` → `10.20.30.x`, `DVNTM-IOTV` → `10.20.31.x`,
`DVNTM-GUEST` → `10.20.40.x`, each with internet access.

This in-place route has not been rehearsed. If a hop comes back without its SSID configuration,
continue by the reset-and-recover path in
[Wireless AP](/docs/runbook/recovery/console-recovery/wireless-ap/).

**Undo:** [Undo phase 3](#undo-phase-3)

## Verification

The change is complete when every point under [Goal](#goal) holds. The switch checks are its
procedure's step 4, and the AP checks are the per-hop version and the per-SSID client test
above. Afterwards, the controller should list the AP on `1.3.11`; it will still be pending, since
adoption is out of scope.

## Undo

### Undo phase 1

[Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/): restore the
pre-upgrade snapshot and start it on 6.2.14.11, or on 6.1 as the last resort. Anything
configured on 6.3 since the snapshot is lost.

### Undo phase 2

1.20.1 stays on flash. Point the boot configuration back at it and reboot —
[Access Switch → Rollback](/docs/runbook/recovery/console-recovery/access-switch/#rollback).
The configuration is kept.

### Undo phase 3

**No undo past 1.3.3.** TP-Link state that a downgrade from 1.3.3 needs their support, which
makes that hop the point of no return for the whole change. No downgrade path is recorded for
the 1.2.5 hop either.

---

## Outcome

### Phase 1 — 2026-09-10

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

The controller was down for about two minutes. No device was adopted, so nothing on the site depended on it being up.

**Found along the way:** the controller has never adopted the switch. The AP has been pending
since 2026-03-24, when it was forgotten with a configuration reset. Neither changes this plan.

### Phases 2 and 3

Not yet run.

## Follow-ups

- [ ] **Schedule phases 2 and 3**, in one window, with the operator on site.
- [x] **Decided who owns the switch's configuration:** inventory owns it, and the controller
  applies it through its Open API — [ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/). Adoption follows that record's order.
- [ ] **Adopt the AP and move the SSIDs to controller provisioning** (`make migration-omada-ssids`),
  retiring CHG-0001's hand-configured SSIDs. A separate change.
- [ ] **Take a fresh controller snapshot before the adoption work.** Today's only snapshot
  predates 6.3, so anything configured on 6.3 before a new one is taken is unprotected.
- [ ] **Move the firmware upgrade procedures into Lifecycle.** They currently sit in the
  console-recovery pages, as the Omada procedure did before it was split.
- [ ] **Fix or retire `playbooks/upgrade-omada.yml`** in the builder collection. It hard-codes a
  fresh install and deletes the controller's data.
