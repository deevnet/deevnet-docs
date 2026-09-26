---
title: "CHG-0005: Wireless AP Firmware and Omada Adoption"
weight: 5
---

# CHG-0005: Wireless AP Firmware and Omada Adoption

| | |
|---|---|
| **Date** | 2026-09-15 |
| **Change type** | Migration — the AP moves from standalone to controller-managed |
| **Classification** | Disruptive — wireless is down during each firmware hop and during adoption, and one hop cannot be undone |
| **Status** | **Complete, 2026-09-15.** The AP runs 1.3.11, is adopted and Connected, and serves the three controller-provisioned SSIDs; `DVNTM` was verified on a client landing on 10.20.10.x. PPSK with per-key VLAN binding was **proven on the AP** (phase 6) and then torn down, leaving `DVNTM-IOT` for a follow-up that provisions per-device keys from inventory. |
| **Window** | 2026-09-15, one operator window. Operator on site at the AP; the AP was reached and adopted through the builder on VLAN 99, so no laptop on `gi1/0/2` was needed. |
| **Site** | mobile |
| **Systems** | AP `dv02wap001p01` (EAP650-Outdoor v1); the Omada controller, now a container in the network management VM `dv02nms001v01` on `dv02hyp001p01` (moved off `dv00bld001p01`) ([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/)). **Not** the access switch. |
| **Automation** | Firmware mirrored by inventory #22. Networks, SSIDs and AP settings by `ansible-collection-deevnet.net` `playbooks/omada-wireless.yml`, through the documented Open API ([ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/)). |
| **Risk** | High. The AP's 1.3.3 hop cannot be undone, and adoption replaces the AP's own configuration with the controller's. |
| **Related changes** | [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) — the hand-set SSIDs this retires; [CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/) — the controller upgrade this was split from; [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/) — the switch, deliberately separate |
| **Related incidents** | [INC-0002](/docs/incidents/2026/0002-controller-vm-network-hang/) — the controller VM was silent at the start of this window; Phase 0 recovered it before the change could run |
| **Related runbooks** | [Wireless AP](/docs/runbook/substrate/recovery/console-recovery/wireless-ap/) (the reset-and-recover path); [Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/); [Important URLs](/docs/runbook/substrate/network/important-urls/) |

---

## Summary

The AP ran firmware 1.0.4, from April 2023. Omada could not push VLAN-tagged SSIDs to it, so
[CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) left the four SSIDs configured by
hand in the AP's own web UI — the one piece of the site's network configuration that lived
nowhere but on the device.

This change took the AP to 1.3.11, adopted it into the controller (on 6.3.0.45 since
[CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/)), and had the controller provision
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
  | `DVNTM-IOT` | 30 | `10.20.30.x` — created in phase 6, once its security model is proven |
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
| The reset discards the hand-set SSIDs before the controller can serve replacements | Phase 2 | Accepted: wireless is down from the reset until phase 4. The SSIDs are already in the controller from phase 1, so nothing has to be reconstructed by hand. |
| Adoption replaces the AP's configuration with the controller's, so wireless is off until the controller's SSIDs arrive | Phase 4 | The networks and SSIDs are provisioned in the controller **before** adoption (phase 1) |
| The AP moves address when the controller takes it over | Phase 4 | The trunk it sits on is native 99, so management stays untagged on 99. OPNsense already reserves `40:ed:00:6f:f9:d4` → `10.20.99.9`, so even a DHCP AP lands on its own address. Phase 5 sets it statically as well. |
| Adoption asks for the AP's standalone credentials, and the vault has none | Phase 4 | The reset in phase 2 sets a new admin account; phase 3 records it in the vault before phase 4 runs |
| The controller upgrades firmware on its own after adoption | Phase 4 | `autoUpgrade` off at site level. Checked on 2026-09-10, but the controller has been reset since, so it is checked again (prerequisite) |
| Something on 6.3 goes wrong with devices adopted | After | A fresh controller snapshot is taken just before adoption |

## Prerequisites

- [ ] **The network management VM exists** (`dv02nms001v01`, on `dv02hyp001p01`), running the controller container, per
  [ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/) (added
  2026-09-14). This change adopts the AP into that controller, not the one on the Builder, so the AP
  is adopted once.
  - The items below that name the controller (the Owner account, the Open API client, site
    `autoUpgrade`) were done or planned on the Builder's controller.
  - They are repeated on the new controller before this change runs.
- [x] AP firmware 1.2.5, 1.3.3 and 1.3.11 mirrored and pinned by sha256; all three matched on
  2026-09-10.
- [x] Controller on 6.3.0.45 ([CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/)).
  Reset to a fresh install on 2026-09-11; see the baseline.
- [x] **Owner account**, now on `dv02nms001v01`: created in that controller's setup wizard on
  2026-09-15 (CHG-0008 Step 9) and recorded in `group_vars/network_controllers/vault.yml` as
  `vault_omada_owner_user` / `vault_omada_owner_password`. The controller reports
  `registeredRoot: true`, so it is **cloud-registered**, as the baseline below says. The vault
  holds one controller's credentials, so the Builder controller's Owner is no longer recorded
  there.
- [x] **Open API client** created by the Owner in the web UI (Global View → Settings → Platform
  Integration → Open API), with its id and secret in `group_vars/network_controllers/vault.yml`
  as `vault_omada_openapi_client_id` / `vault_omada_openapi_client_secret`. Done on
  `dv02nms001v01` on 2026-09-15 and verified: a client-credentials request returned a bearer token
  and listed the site.
- [x] **The AP's standalone login** in the vault, as `vault_wap_standalone_user` /
  `vault_wap_standalone_password`. The old login was unrecoverable (a 2026-09-11 adoption was
  refused with `adopt info is wrong`), so the reset-first route was taken. The account set at the
  AP's first login after the 2026-09-15 factory reset (`admin` / `admin11`) is now recorded in
  `group_vars/network_controllers/vault.yml`, and adoption used it successfully.
- [x] **Site `autoUpgrade` off** — confirmed by the operator in the UI (Site Settings → Services)
  before adoption on 2026-09-15. This is a **UI check**: `autoUpgrade` appears nowhere in the
  Open API spec 6.3.0.45 publishes, and `getSiteEntity` does not return it, so no play can assert
  it. The site has **no upgrade schedules** either (`getUpgradeScheduleList`).
- [x] **Wi-Fi keys and client isolation for `DVNTM-IOT` decided.** Both are now settled in
  [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/), which matters
  because `omada-wireless.yml` creates SSIDs and never rewrites one: whatever phase 1 creates is
  what stays.
  - **Keys (question 3, decided 2026-09-15):** per-device PPSK keys, each bound to the device's
    trust-class VLAN, issued through the Deevnet API. Substrate automation issues them until the
    API can. **This change still has to prove PPSK works on this AP**, including its WPA version;
    a shared key is the fallback if it does not.
  - **Isolation (question 4, decided 2026-09-14):** best effort, credentials first. Wireless
    clients get Guest Network plus an EAP ACL permit for the broker **only if the device test shows
    it works**; wired devices on VLAN 30 stay unisolated.
- [x] `playbooks/omada-wireless.yml` run in plan mode, and its report read. Done 2026-09-15.
- [x] A wired path onto VLAN 99 that does not depend on the AP. The operator port `gi1/0/2` is
  free and untagged on 99 (confirmed 2026-09-15), but the builder at `10.20.99.95` also reaches
  both the AP and the artifact server, so the window is driven through it with one `ssh -L`
  rather than a re-addressed laptop.
- [x] A client device able to join the SSIDs (a spare device on a second connection, kept off
  the control path).

### Baseline, 2026-09-10 and -11

| | |
|---|---|
| AP | `1.0.4 Build 20230421`; answers at `https://10.20.99.9`. Discovered by the reset controller, not adopted; the 2026-09-11 adoption attempt was refused on the AP's credentials. |
| AP address | OPNsense reserves `40:ed:00:6f:f9:d4` → `10.20.99.9` |
| Controller | Now `dv02nms001v01`'s container, `6.3.0.45`, set up on 2026-09-15 with a local Owner, the `a_autoprov` automation account and an Open API client (CHG-0008 Steps 8–9). The Builder's controller below is the cold fallback. `6.3.0.45`. **Reset to a fresh install on 2026-09-11**: the Owner login had been lost, and nothing on the controller was worth keeping. The old data and logs are kept on the host under `/opt/omada-controller-backup/pre-reset-2026-09-11/`. The new Owner is cloud-registered (`registeredRoot: true`). `a_autoprov` has not been recreated; this change doesn't need it. The March networks went with the reset, so phase 1 creates all four wireless networks. |
| Access switch | Standalone. `gi1/0/4` (the AP) is a trunk: native 99, allowed 10, 30, 31, 40, 99. `gi1/0/2` (the operator port) is untagged VLAN 99. |

---

## Procedure

### Phase 1 — Provision the controller from inventory · *no device affected*

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/omada-wireless.yml -e '{"omada_segment_skip":["iot"]}'
ansible-playbook playbooks/omada-wireless.yml -e '{"omada_segment_skip":["iot"]}' -e omada_apply=true
```

This creates any missing network and SSID from inventory. The AP is not adopted yet, so nothing
reaches it. Objects the controller holds that inventory doesn't declare are reported and left in
place.

{{< hint warning >}}
**`DVNTM-IOT` is deliberately held back until phase 6.** `omada-wireless.yml` creates an SSID
once and never rewrites it, so a segment whose security model is still being decided must not be
created with the wrong one "for now". `omada_segment_skip` — added for this change — leaves the
`iot` segment out of the desired set; dropping the `-e` puts it back.
{{< /hint >}}

**Verify:** a second plan run reports nothing to add.

**Done 2026-09-15.** Created LAN networks `trusted` (VLAN 10), `iot_vendor` (31) and `guest`
(40), and SSIDs `DVNTM` → VLAN 10, `DVNTM-IOTV` → 31, `DVNTM-GUEST` → 40 (guest network on), all
WPA-Personal in the `Default` WLAN group. A second plan run reports nothing to add.

**Undo:** [Undo phase 1](#undo-phase-1)

### Phase 2 — Factory reset, then firmware 1.0.4 → 1.2.5 → 1.3.3 → 1.3.11

The AP's standalone login is unknown and not recoverable, so this is the **reset-first** route
from [Wireless AP](/docs/runbook/substrate/recovery/console-recovery/wireless-ap/) steps 2–4, not the
in-place hops originally planned. Wireless is down from the reset until phase 4 completes.

1. **Check the AP's switch port before resetting anything.** A drifted trunk looks exactly like a
   dead AP, and a reset will not fix it. On `dv02acc001p01`:
   `show interface switchport gigabitEthernet 1/0/4` → PVID 99, with 10, 30, 31 and 40 tagged and
   99 untagged. *(Confirmed correct 2026-09-15.)*
2. **Press and hold the reset button** until the AP restarts.
3. **Confirm the reset took, then find it.** The reset wipes the managed address, so `10.20.99.9`
   drops for ~1 minute, then **returns on `10.20.99.9` via the AP's DHCP reservation** once it
   finishes booting — a factory-default EAP does DHCP first, and OPNsense reserves its MAC. It may
   briefly show a `boot` splash on `192.168.0.254` mid-boot; that is transient. A fresh AP serves
   **HTTP** and forces a first-login account: set it, and record it as
   `vault_wap_standalone_user` / `vault_wap_standalone_password`. Only if DHCP does not answer
   does it stay on `192.168.0.254`, which needs a temporary `192.168.0.1/24` on the builder's
   `enp4s0` to reach.
4. **Log in with `admin`/`admin` and record the admin account the firmware makes you set.** That
   is what phase 3 puts in the vault and what adoption asks for.
5. **Hop in order**, uploading each `.bin` (not the `.zip`) under **System → Firmware Update**
   and confirming **Status → Device Information → Firmware Version** before starting the next:
   `1.2.5`, then `1.3.3`, then `1.3.11`.

**Undo:** [Undo phase 2](#undo-phase-2)

### Phase 3 — Record the credentials, check autoUpgrade, snapshot

1. Put the AP's new admin account in
   `group_vars/network_controllers/vault.yml` as `vault_wap_standalone_user` /
   `vault_wap_standalone_password`. Phase 4 fails on an undefined variable without them.
2. Confirm site **autoUpgrade is off** in the controller UI — the guard against the controller
   flashing the AP on its own once it is adopted, and not assertable from the API.
3. Per [Omada Controller Upgrade → step 2](/docs/runbook/substrate/lifecycle/omada-controller-upgrade/#2-record-stop-snapshot):
   stop the controller cleanly, archive `/opt/omada-controller`, and start it again. That gives a
   recovery point on 6.3 from just before any device is adopted.

### Phase 4 — Adopt the AP

```bash
ansible-playbook playbooks/omada-wireless.yml \
  -e '{"omada_segment_skip":["iot"]}' -e omada_apply=true -e omada_adopt=true
```

The play adopts only when the controller reports the AP as *pending*, then polls until
*connected*. The controller then pushes the phase 1 SSIDs, and the AP's hand-set configuration is
gone.

If the AP does not reappear after the reset, **forget its stale pending entry** in the controller
and let it be rediscovered — the pre-reset record, pinned at firmware 1.0.4, is the likeliest
thing to confuse adoption. Discovery is L2 on VLAN 99 and `dv02nms001v01` already opens
29810/UDP and 29811–29817/TCP, so an inform URL should not be needed; if one is, it is
`https://10.20.99.40`, **not** the builder's cold spare.

**Undo:** [Undo phase 4](#undo-phase-4)

### Phase 5 — Set the AP from inventory

```bash
ansible-playbook playbooks/omada-wireless.yml -e '{"omada_segment_skip":["iot"]}' -e omada_apply=true
```

With the AP now adopted, this sets its name and static address. The playbook puts the SSIDs in
the site's primary WLAN group, which an adopted AP joins, so there is no group to assign.

### Phase 6 — Prove PPSK on `DVNTM-IOT`

This is the question phase 1 held the segment back for. Do it by hand, before any automation owns
the SSID, because everything here is deletable and the playbook's creation is not.

**PPSK is in the documented Open API.** From the spec the running controller publishes at
`/v3/api-docs/00%20All`, checked 2026-09-15 on 6.3.0.45:

- `CreateSsidOpenApiVO.security` — *"SSID security mode; Security should be a value as follows:
  0: None; 2: WPA-Enterprise; 3: WPA-Personal; **4: PPSK without RADIUS**; 5: PPSK with RADIUS."*
- `PpskSetting` — required `name` and `psk`; optional **`mac`** (*"Mac Bound With PSK"*) and
  **`vlan`** (*"Vlan Bound With PSK, should be within the range of 1-4094"*).
- Site-scoped endpoints `createPPSKProfile`, `addPSKsToPPSKProfile`, `getPPSKProfiles`,
  `deletePPSKProfile`, and `SsidPpskSettingOpenApiVO.ppskProfileId` to bind a profile to an SSID.

So the controller side of [ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/)
question 3 — per-device keys, each bound to the device's trust-class VLAN — is available through
documented calls, not UI-only. **What is unproven is the device side:** whether the
EAP650-Outdoor on 1.3.11 honors a PPSK profile in practice.

1. Create one PPSK profile with two test keys: one `vlan: 30`, one `vlan: 31`.
2. Create `DVNTM-IOT` in the `Default` WLAN group with `security: 4` and
   `ppskSetting.ppskProfileId` set to that profile.
3. **Test from a client.** The question is not whether it associates but whether **the key
   decides the VLAN**: join with the VLAN-30 key and confirm a `10.20.30.x` lease, then with the
   VLAN-31 key and confirm `10.20.31.x`.
4. **Test the isolation shape** from ADR-0011 question 4: Guest Network on, plus an EAP ACL
   permitting the broker at `10.20.35.20` (1883/8883). Keep it only if an isolated client can
   still reach the broker. Wired VLAN 30 devices stay unisolated either way.

**If PPSK holds:** the automation path is documented — extend `omada-wireless.yml` with the
endpoints above and drop `omada_segment_skip`.

**If it does not:** delete the profile and the SSID, run one apply with no skip so the playbook
creates `DVNTM-IOT` as WPA-Personal from `deevnet_wifi_psk.iot`, and record that ADR-0011's
stated shared-key fallback was taken on evidence.

**Undo:** delete the PPSK profile and the SSID. Nothing else depends on them.

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
did, by the [Wireless AP](/docs/runbook/substrate/recovery/console-recovery/wireless-ap/) recovery path.
To undo the controller's side as well, restore the phase 3 snapshot.

---

## Outcome

Done on 2026-09-15, in one operator window.

**Firmware.** The AP would not hold a factory reset until the button was held with a proper tool
(the iFixit kit, not a paperclip); the first two attempts were only power cycles. Once it reset,
it came up `firstLogin: true` on `10.20.99.9` **via DHCP** — a factory-default EAP does DHCP
first, and OPNsense reserves its MAC — not on the static `192.168.0.254` the old runbook assumed.
The hops `1.0.4 → 1.2.5 → 1.3.3 → 1.3.11` each went cleanly (~48 s reboot each); the one first-boot
that stalled on a `boot` splash cleared with a PoE power cycle.

**Adoption.** Discovery over L2 on VLAN 99 found the AP as *pending* ~30 s after the final boot,
no inform URL needed. `omada-wireless.yml -e omada_adopt=true` adopted it with the vaulted
standalone credentials, and it went **Connected** on 1.3.11. The name and static address were set
from inventory on a second apply.

**SSIDs.** `DVNTM`, `DVNTM-IOTV` and `DVNTM-GUEST` are controller-provisioned from inventory.
`DVNTM` was verified on a client: association and a `10.20.10.x` lease. The AP's four hand-set
SSIDs are gone — the last device-only piece of the site's network config is now in inventory.

**PPSK (phase 6) — proven.** A PPSK-without-RADIUS profile with two keys (bound to VLAN 30 and
VLAN 31) was created through the documented Open API and bound to a temporary `DVNTM-IOT` SSID. A
spare client joined with each key in turn and landed on the matching subnet — `10.20.30.100` with
the VLAN-30 key, `10.20.31.100` with the VLAN-31 key. **The key decides the VLAN on this AP**, so
[ADR-0011](/docs/architecture/decisions/0011-edge-devices-application-owned/) question 3 (per-device
PPSK keys, each pinned to a trust-class VLAN) is proven on real hardware, and the shared-key
fallback is not needed. The test SSID, its profile and the temporary VLAN-30 network were then
deleted, returning the controller to its post-adoption state.

**Two Open API defects found and worked around:**
- `ip-setting` rejects `mode: Static` with `errorCode -1001`; it wants lowercase `static`, though
  the spec's own description reads `Static; DHCP`. Fixed in `omada-wireless.yml`.
- Creating a `security: 4` (PPSK) SSID needs the `pskSetting` encryption block
  (`versionPsk`/`encryptionPsk`/`gikRekeyPskEnable`) **in addition to** `ppskSetting.ppskProfileId`;
  without it the controller returns an opaque `errorCode -1`. The spec marks only `ppskSetting` as
  relevant for security 4.

## Follow-ups

- [x] **Done by [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/), 2026-09-18.**
  Provision `DVNTM-IOT` for real. `omada-wireless.yml` now manages a PPSK profile and the `iot`
  SSID from inventory, and the `iot` skip is gone. **One thing changed from what this follow-up
  assumed:** the keys are not per-device and they do not come from inventory. They are one per
  tenant per trust class, issued by the Deevnet API into a profile inventory creates empty
  ([ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §3, amended). The `pskSetting`
  workaround this record found was needed exactly as described.
- [x] **Done by [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/), 2026-09-18.**
      Retire `playbooks/migration/13-omada-ssids.yml`, which used undocumented calls, once
  `omada-wireless.yml` has run for real.
- [ ] Move the AP firmware procedure into Lifecycle. It sits in the console-recovery page today.
