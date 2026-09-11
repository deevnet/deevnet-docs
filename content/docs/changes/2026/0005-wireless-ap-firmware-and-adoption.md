---
title: "CHG-0005: Wireless AP Firmware and Omada Adoption"
weight: 5
---

# CHG-0005: Wireless AP Firmware and Omada Adoption

| | |
|---|---|
| **Date** | Not yet scheduled |
| **Change type** | Migration — the AP moves from standalone to controller-managed |
| **Classification** | Disruptive — wireless is down during each firmware hop and during adoption, and one hop cannot be undone |
| **Status** | **Planned** |
| **Window** | To be scheduled. Operator on site, with a laptop on the operator port `gi1/0/2`. |
| **Site** | mobile |
| **Systems** | AP `dv02wap001p01` (EAP650-Outdoor v1); the Omada controller on `dv00bld001p01`. **Not** the access switch. |
| **Automation** | Firmware mirrored by inventory #22. Networks, SSIDs and AP settings by `ansible-collection-deevnet.net` `playbooks/omada-wireless.yml`, through the documented Open API ([ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/)). |
| **Risk** | High. The AP's 1.3.3 hop cannot be undone, and adoption replaces the AP's own configuration with the controller's. |
| **Related changes** | [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) — the hand-set SSIDs this retires; [CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/) — the controller upgrade this was split from; [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/) — the switch, deliberately separate |
| **Related incidents** | None |
| **Related runbooks** | [Wireless AP](/docs/runbook/recovery/console-recovery/wireless-ap/) (the reset-and-recover path); [Omada Controller Recovery](/docs/runbook/recovery/omada-controller-recovery/); [Important URLs](/docs/runbook/network/important-urls/) |

---

## Summary

The AP runs firmware 1.0.4, from April 2023. Omada could not push VLAN-tagged SSIDs to it, so
[CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) left the four SSIDs configured by
hand in the AP's own web UI. That is the one piece of the site's network configuration that
lives nowhere but on the device.

This change takes the AP to 1.3.11, adopts it into the controller, which runs 6.3.0.45 since
[CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/), and has the controller provision
the SSIDs from inventory through its documented Open API, per
[ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/).

**The access switch is not touched.** It stays standalone, configured by `switch_vlans`, as
ADR-0009 allows for a switch that has not been adopted. Its firmware is
[CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/), and its adoption is a later
change again.

## Goal

The end state that counts as done:

- The AP runs **1.3.11**, reached through 1.2.5 and 1.3.3.
- The AP is **adopted and connected** in the controller, named `dv02wap001p01`, at `10.20.99.9`,
  with its management untagged on VLAN 99.
- **The four SSIDs come from inventory**, provisioned by the controller, not set by hand. Their
  names come from `wifi_ssid` in `deevnet_vlans` and their keys from `deevnet_wifi_psk`:

  | SSID | VLAN | Client lands on |
  |---|---|---|
  | `DVNTM` | 10 | `10.20.10.x` |
  | `DVNTM-IOT` | 30 | `10.20.30.x` |
  | `DVNTM-IOTV` | 31 | `10.20.31.x` |
  | `DVNTM-GUEST` | 40 | `10.20.40.x` |

- The access switch is unchanged.

## Scope

**In scope:** the AP's firmware; the AP's adoption; the controller's networks and SSIDs for the
four wireless segments; the AP's name and address.

**Out of scope:** the access switch (firmware is CHG-0006, adoption later, per ADR-0009) and the
home site.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Each AP build declares a minimum prior version | Phase 2 | Hops in order, confirming the version between each |
| The 1.3.3 hop is irreversible — TP-Link state a downgrade needs their support | Phase 2 | All three files mirrored and pinned in advance. This hop is the change's point of no return. |
| An in-place hop loses the standalone SSID configuration | Phase 2 | Wireless is down for a while, not lost for good: the SSIDs come from the controller after adoption anyway. Worst case is the reset-and-recover path in [Wireless AP](/docs/runbook/recovery/console-recovery/wireless-ap/). |
| Adoption replaces the AP's configuration with the controller's, so wireless is off until the controller's SSIDs arrive | Phase 4 | The networks and SSIDs are provisioned in the controller **before** adoption (phase 1) |
| The AP moves address when the controller takes it over | Phase 4 | The trunk it sits on is native 99, so management stays untagged on 99. OPNsense already reserves `40:ed:00:6f:f9:d4` → `10.20.99.9`, so even a DHCP AP lands on its own address. Phase 5 sets it statically as well. |
| Adoption asks for the AP's standalone credentials, and the vault has none | Phase 4 | Recorded in the vault before the window (prerequisite) |
| The controller upgrades firmware on its own after adoption | Phase 4 | `autoUpgrade` off at site level. Checked on 2026-09-10, but the controller has been reset since, so it is checked again (prerequisite) |
| Something on 6.3 goes wrong with devices adopted | After | A fresh controller snapshot is taken just before adoption |

## Prerequisites

- [x] AP firmware 1.2.5, 1.3.3 and 1.3.11 mirrored and pinned by sha256; all three matched on
  2026-09-10.
- [x] Controller on 6.3.0.45 ([CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/)).
  Reset to a fresh install on 2026-09-11; see the baseline.
- [x] **Owner account** on the reset controller, created in the setup wizard on 2026-09-11 and
  recorded in `group_vars/network_controllers/vault.yml` as `vault_omada_owner_user` /
  `vault_omada_owner_password`.
- [ ] **Open API client** created by the Owner in the web UI (Global View → Settings → Platform
  Integration → Open API), with its id and secret in `group_vars/network_controllers/vault.yml`
  as `vault_omada_openapi_client_id` / `vault_omada_openapi_client_secret`.
- [ ] **The AP's current standalone login** in the same vault, as `vault_wap_standalone_user` /
  `vault_wap_standalone_password`. **Not known.** On 2026-09-11 an adoption from the reset
  controller was refused on the AP's credentials (the controller log reads `adopt info is
  wrong`). If the login can't be recovered, the way on is a factory reset by the
  [Wireless AP](/docs/runbook/recovery/console-recovery/wireless-ap/) path, which replaces
  phase 2's in-place hops with that page's reset-first route. Not yet decided.
- [ ] **Site `autoUpgrade` off** on the reset controller. The 2026-09-10 check was made on the
  controller that has since been wiped.
- [ ] `playbooks/omada-wireless.yml` run in plan mode, and its report read.
- [ ] Laptop on `gi1/0/2`, taking an address from `10.20.99.200–230`, with the three `.bin` files
  already downloaded to it.
- [ ] A client device able to join each of the four SSIDs.

### Baseline, 2026-09-10 and -11

| | |
|---|---|
| AP | `1.0.4 Build 20230421`; answers at `https://10.20.99.9`. Discovered by the reset controller, not adopted; the 2026-09-11 adoption attempt was refused on the AP's credentials. |
| AP address | OPNsense reserves `40:ed:00:6f:f9:d4` → `10.20.99.9` |
| Controller | `6.3.0.45`. **Reset to a fresh install on 2026-09-11**: the Owner login had been lost, and nothing on the controller was worth keeping. The old data and logs are kept on the host under `/opt/omada-controller-backup/pre-reset-2026-09-11/`. The new Owner is cloud-registered (`registeredRoot: true`). `a_autoprov` has not been recreated; this change doesn't need it. The March networks went with the reset, so phase 1 creates all four wireless networks. |
| Access switch | Standalone. `gi1/0/4` (the AP) is a trunk: native 99, allowed 10, 30, 31, 40, 99. `gi1/0/2` (the operator port) is untagged VLAN 99. |

---

## Procedure

### Phase 1 — Provision the controller from inventory · *no device affected*

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/omada-wireless.yml                    # plan: reports, writes nothing
ansible-playbook playbooks/omada-wireless.yml -e omada_apply=true
```

This creates any missing network for VLANs 10, 30, 31 and 40, and any missing SSID, from
inventory. The AP is not adopted yet, so nothing reaches it. Objects the controller holds that
inventory doesn't declare are reported and left in place.

**Verify:** a second plan run reports nothing to add.

**Undo:** [Undo phase 1](#undo-phase-1)

### Phase 2 — AP firmware 1.0.4 → 1.2.5 → 1.3.3 → 1.3.11 · *in place*

Through the AP's own web UI at `https://10.20.99.9`, from the laptop. There is no factory reset
first; the aim is that the standalone SSIDs keep serving between hops. The file handling
follows [Wireless AP → step 4](/docs/runbook/recovery/console-recovery/wireless-ap/#4-upgrade-the-firmware-before-adopting),
which describes the same upload for an AP that has been reset.

For each hop, in order — `1.2.5`, `1.3.3`, `1.3.11`:

1. Upload the hop's `.bin` (not the `.zip`) under **System → Firmware Update**. The AP reboots,
   and wireless is down until it is back.
2. Confirm **Status → Device Information → Firmware Version** shows the hop's version before
   starting the next.

This in-place route has not been rehearsed. If a hop comes back without its configuration,
carry on: phase 4 replaces that configuration anyway.

**Undo:** [Undo phase 2](#undo-phase-2)

### Phase 3 — Snapshot the controller

Per [Omada Controller Upgrade → step 2](/docs/runbook/lifecycle/omada-controller-upgrade/#2-record-stop-snapshot):
stop the controller cleanly, archive `/opt/omada-controller`, and start it again. That gives a
recovery point on 6.3 from just before any device is adopted.

### Phase 4 — Adopt the AP

Run `omada-wireless.yml -e omada_apply=true -e omada_adopt=true`, or click **Adopt** in the
controller and give the standalone credentials when asked. Wait for **Connected**. The controller
then pushes the phase 1 SSIDs, and the AP's hand-set configuration is gone.

**Undo:** [Undo phase 4](#undo-phase-4)

### Phase 5 — Set the AP from inventory

```bash
ansible-playbook playbooks/omada-wireless.yml -e omada_apply=true
```

With the AP now adopted, this sets its name and static address. The playbook puts the SSIDs in
the site's primary WLAN group, which an adopted AP joins, so there is no group to assign.

## Verification

- **From a client, on each SSID:** a lease on the right subnet (see [Goal](#goal)), and internet
  access.
- **The controller** lists the AP as Connected, on `1.3.11`, named `dv02wap001p01`, at `10.20.99.9`.
- **A plan run** of `omada-wireless.yml` reports no drift.
- **The access switch** is untouched: `show image-info` and the running config are as before.

## Undo

### Undo phase 1

Nothing is adopted during phase 1, so the objects it creates affect no device. They can stay. The
playbook reports the ones inventory stops declaring, and leaves them in place.

### Undo phase 2

**No undo past 1.3.3.** TP-Link state that a downgrade from 1.3.3 needs their support. No
downgrade path is recorded for 1.2.5 either.

### Undo phase 4

**Forget** the AP in the controller. It resets to factory defaults, and the SSIDs are then set
by hand again, as [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/port-migration/#step-13-ap-ssid-configuration)
did, by the [Wireless AP](/docs/runbook/recovery/console-recovery/wireless-ap/) recovery path.
To undo the controller's side as well, restore the phase 3 snapshot.

---

## Outcome

Not yet run.

## Follow-ups

- [ ] Retire `playbooks/migration/13-omada-ssids.yml`, which used undocumented calls, once
  `omada-wireless.yml` has run for real.
- [ ] Move the AP firmware procedure into Lifecycle. It sits in the console-recovery page today.
