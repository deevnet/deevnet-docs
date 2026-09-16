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
| **Related runbooks** | [Access Switch → Firmware upgrade](/docs/runbook/recovery/console-recovery/access-switch/#firmware-upgrade); [Operator Access](/docs/runbook/network/operator-access/); [Important URLs](/docs/runbook/network/important-urls/) |

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
- [ ] Operator on site, connected to the builder through the travel router rather than the switch,
  per [Operator Access](/docs/runbook/network/operator-access/). The SSH session survives the reboot,
  and its tunnel carries the switch's web UI (`https://localhost:8443`) for the upload.
  **Backup:** a laptop on the operator port `gi1/0/2`
  ([Operator Access → Backup](/docs/runbook/network/operator-access/#backup-the-operator-port)).
  That path goes through the switch, so it's fine for the backup and the upload, but it drops at
  the reboot along with everything else.
- [ ] The `.bin` downloaded to the laptop beforehand, with sha256
  `a01034c5409bd14c9066db857d192807bdfe85788472ed12bb5778159c7a4e0d`. That is the file inside the
  pinned zip, checked on 2026-09-16.
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
2. **Upload into the backup image** from `https://10.20.99.10` (`https://localhost:8443` through the
   tunnel) — the `.bin`, with the auto-reboot box **unchecked**.
3. **Boot from it** — set the next startup image, then reboot at a moment of the operator's
   choosing. Before the reboot, read
   [Keeping the builder online](#keeping-the-builder-online-during-the-reboot).
4. **Verify** — see below.

### Keeping the builder online during the reboot

The builder has two uplinks. Only one of them goes through the switch.

| Interface | Address | Path | Role today |
|---|---|---|---|
| `enp4s0` | `10.20.99.95/24`, static | Switch `gi1/0/16` → OPNsense `10.20.99.1` | Preferred default route and preferred DNS (`ipv4.dns-priority 10`) |
| `enp1s0` | `192.168.8.x`, DHCP | Travel router `dv02edg001p01` at `192.168.8.1`, not through the switch | Second default route (higher metric); DNS `192.168.8.1`, not used while `enp4s0` is up |

On 2026-09-16, `enp1s0` was checked on its own: it pings `1.1.1.1`, reaches
`https://api.anthropic.com` over HTTPS, and `192.168.8.1` resolves public names. An operator
session to the builder over the travel router's wireless doesn't touch the switch, so it
survives the reboot. See [Operator Access](/docs/runbook/network/operator-access/).

**What should happen:** when the switch reboots, `enp4s0` loses its link. After a few seconds,
NetworkManager takes that connection down and removes its default route and its DNS server. New
connections from the builder then go out through `enp1s0`. Connections that were open when the
link dropped are lost. When the switch returns, `enp4s0` connects again on its own (autoconnect
is on) and takes over as the preferred path. This is expected behaviour, not tested: it wasn't
tested because the builder serves artifacts on `enp4s0`.

**Check it during the outage:**

```bash
ip route get 1.1.1.1              # expect: via 192.168.8.1 dev enp1s0
resolvectl status | grep -E 'Link|Current DNS|Default Route'   # expect enp1s0 as the default route
getent hosts api.anthropic.com    # public names still resolve
```

**If it doesn't fall back** (the route still points at `enp4s0`, or names don't resolve), force
it:

```bash
sudo nmcli con down enp4s0        # routes and DNS move to enp1s0
# ... wait until the switch has booted ...
sudo nmcli con up enp4s0          # the switch path is preferred again
ping 10.20.99.10
```

`enp4s0` is also the builder's only route to the switch and every site VLAN. While it's down,
`ping 10.20.99.10` can't tell you the switch is back. Watch the switch's LEDs, or retry
`nmcli con up enp4s0` until it succeeds, then ping. Bring it back up before verifying.

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
