---
title: "CHG-0006: Access Switch Firmware Upgrade"
weight: 6
---

# CHG-0006: Access Switch Firmware Upgrade

| | |
|---|---|
| **Date** | Not yet scheduled |
| **Change type** | Upgrade |
| **Classification** | Disruptive — the reboot drops every wired path on site |
| **Status** | **Planned**, after [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) |
| **Window** | To be scheduled, with the operator on site |
| **Site** | mobile |
| **Systems** | Access switch `dv02acc001p01` (SG2218, hardware 1.20) |
| **Automation** | Firmware mirrored by inventory #23; procedure in docs #29 |
| **Risk** | High. The switch reboot takes the builder, the controller and Ansible offline with everything else. |
| **Related changes** | [CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/) — this was its phase 2 until 2026-09-11 |
| **Related incidents** | None |
| **Related runbooks** | [Access Switch → Firmware upgrade](/docs/runbook/recovery/console-recovery/access-switch/#firmware-upgrade); [Important URLs](/docs/runbook/network/important-urls/) |

---

## Summary

The access switch runs firmware 1.20.1, from January 2024. Current for its hardware is 1.20.24,
from May 2026: one hop, with no minimum prior version and nothing irreversible. This change is
the firmware only. The switch stays standalone, configured by `switch_vlans`. Adopting it into
the controller is a later change under
[ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/).

It was phase 2 of [CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/) until the
AP work was split out to go first.

## Goal

- The switch runs **1.20.24** in one image slot, with **1.20.1** kept in the other as the
  rollback.
- Its configuration is unchanged, and Ansible still connects.
- STP and LLDP are in a state that was chosen rather than inherited from new defaults.

## Scope

**In scope:** the switch's firmware. **Out of scope:** adopting it into Omada, and any
configuration change.

## Risk and impact

| Risk | Guard |
|---|---|
| The reboot drops every wired path, the builder's included — the controller, Ansible and the browser used for the upload | Upload without auto-reboot, so the outage starts when the operator chooses. The hypervisors are not clustered, so nothing fences. |
| **There is no console port.** The SG2218 has LEDs, a reset button, RJ45 ports and SFP slots, and nothing else ([installation guide](https://static.tp-link.com/upload/manual/2023/202305/20230511/7106510303_TL-SG2218(UN)_IG.pdf)). | The way back from a bad state is the dual image (see [Undo](#undo)) or the reset button. After a reset, nothing on site hands out an address on VLAN 1, so the laptop needs a static `192.168.0.2/24` to reach the switch at `192.168.0.1`. |
| Automation loses the switch: it is reached over legacy SSH key exchange, and 1.20.4 (OpenSSL) and 1.20.19 (SSH fix) are where that could change | Verification leads with "does Ansible connect"; 1.20.1 stays on flash as the rollback |
| New defaults come up under an unchanged config: STP is on by default from 1.20.9, LLDP from 1.20.4 | Baseline recorded below: both **disabled** today |

## Prerequisites

- [x] Firmware 1.20.24 mirrored and pinned by sha256; it matched on 2026-09-10.
- [ ] Operator on site, with the laptop on `gi1/0/2` and the `.bin` downloaded to it beforehand.
- [ ] Vault decrypted, so Ansible can verify the switch before and after.
- [ ] `show system-info`, `show image-info` and the running config captured on the day.

### Baseline, 2026-09-10

| | |
|---|---|
| Firmware | `1.20.1 Build 20240115` in `image2.bin` (boots); `image1.bin` holds the factory `1.1.3` |
| STP | `Spanning tree is disabled` |
| LLDP | `LLDP Status: Disabled` |
| Management | `10.20.99.10` on VLAN 99; OPNsense also reserves `5c:62:8b:0c:40:ec` → `10.20.99.10` |

---

## Procedure

Follow [Access Switch → Firmware upgrade](/docs/runbook/recovery/console-recovery/access-switch/#firmware-upgrade):

1. **Record where it starts** — capture system info, image info and the running config.
2. **Upload into the backup image** from `https://10.20.99.10` — the `.bin`, with the auto-reboot
   box **unchecked**.
3. **Boot from it** — set the next startup image, then reboot at a moment of the operator's
   choosing.
4. **Verify** — see below.

## Verification

- Version and image slots: `1.20.24` boots, and `1.20.1` is in the other slot.
- Ansible connects.
- STP and LLDP compared with the baseline above.
- The running config compared with step 1.
- The reachability pings.
- One run of `switch-vlans.yml`.

## Undo

1.20.1 stays on flash. Point the boot configuration back at it and reboot —
[Access Switch → Rollback](/docs/runbook/recovery/console-recovery/access-switch/#rollback). The
configuration is kept.

---

## Outcome

Not yet run.

## Follow-ups

- [ ] Confirm whether 1.20.17 and later force a password change at first login after a reset.
  That can only be seen when the switch is reset, which the eventual adoption change will do.
- [ ] Move the switch firmware procedure into Lifecycle. It sits in the console-recovery page
  today.
