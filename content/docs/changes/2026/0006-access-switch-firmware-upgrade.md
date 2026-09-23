---
title: "CHG-0006: Access Switch Firmware Upgrade"
weight: 6
---

# CHG-0006: Access Switch Firmware Upgrade

| | |
|---|---|
| **Date** | 2026-09-16 |
| **Change type** | Upgrade |
| **Classification** | Disruptive — the reboot drops every wired path on site |
| **Status** | **Complete, 2026-09-16.** The switch runs 1.20.24 from `image1.bin`, with 1.20.1 kept in `image2.bin` as the rollback. The configuration came through unchanged and matches inventory, and Ansible connects. STP is still disabled. LLDP came up enabled under the new default and was kept on deliberately; it is now declared in inventory. |
| **Window** | 2026-09-16, one operator window. The operator was on site and reached the builder through the travel router. The switch was down from 08:15:32 to 08:17:11 EDT, about 100 seconds. |
| **Site** | mobile |
| **Systems** | Access switch `dv02acc001p01` (SG2218, hardware 1.20) |
| **Automation** | Firmware mirrored by inventory #23; procedure in docs #29 and #70. LLDP declared by net #21 (`switch_lldp`) and inventory #33. |
| **Risk** | High. The switch reboot takes the builder, the controller and Ansible offline with everything else. |
| **Related changes** | [CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/) — this was its phase 2 until 2026-09-11 |
| **Related incidents** | None |
| **Related runbooks** | [Access Switch → Firmware upgrade](/docs/runbook/substrate/recovery/console-recovery/access-switch/#firmware-upgrade); [Operator Access](/docs/runbook/substrate/network/operator-access/); [Important URLs](/docs/runbook/substrate/network/important-urls/) |

---

## Summary

The access switch ran firmware 1.20.1, from January 2024. Current for its hardware is 1.20.24,
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
- [x] Operator on site, connected to the builder through the travel router rather than the switch,
  per [Operator Access](/docs/runbook/substrate/network/operator-access/). The SSH session survives the reboot,
  and its tunnel carries the switch's web UI (`https://localhost:8443`) for the upload.
  **Backup:** a laptop on the operator port `gi1/0/2`
  ([Operator Access → Backup](/docs/runbook/substrate/network/operator-access/#backup-the-operator-port)).
  That path goes through the switch, so it's fine for the backup and the upload, but it drops at
  the reboot along with everything else.
- [x] The `.bin` downloaded to the laptop beforehand, with sha256
  `a01034c5409bd14c9066db857d192807bdfe85788472ed12bb5778159c7a4e0d`. That is the file inside the
  pinned zip, checked on 2026-09-16.
- [x] Vault decrypted, so Ansible can verify the switch before and after.
- [ ] `show system-info`, `show image-info` and the running config captured on the day.
  **Not done.** A configuration backup was taken from the web UI, but not the CLI captures. The
  config after the upgrade was checked against inventory instead; see [Outcome](#outcome).

### Baseline, 2026-09-10

| | |
|---|---|
| Firmware | `1.20.1 Build 20240115` in `image2.bin` (boots); `image1.bin` holds the factory `1.1.3` |
| STP | `Spanning tree is disabled` |
| LLDP | `LLDP Status: Disabled` |
| Management | `10.20.99.10` on VLAN 99; OPNsense also reserves `5c:62:8b:0c:40:ec` → `10.20.99.10` |

---

## Procedure

Follow [Access Switch → Firmware upgrade](/docs/runbook/substrate/recovery/console-recovery/access-switch/#firmware-upgrade):

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
survives the reboot. See [Operator Access](/docs/runbook/substrate/network/operator-access/).

**What happened on 2026-09-16:** when the switch rebooted, `enp4s0` lost its link, and in the
same second NetworkManager logged `set 'enp1s0' (enp1s0) as default for IPv4 routing and DNS`.
New connections from the builder went out through `enp1s0`. A connection that is already open
over `enp4s0` doesn't move with it. When the switch returned about 100 seconds later, `enp4s0` connected again
on its own (autoconnect is on), and DNS moved back to `10.20.99.1`.

**The default route did not move back.** Neither connection pins its route metric, so on
reconnecting `enp4s0` was given metric 102, behind `enp1s0`'s 101. Internet traffic from the
builder stayed on the travel router. Traffic to the site VLANs was unaffected, because it uses
the specific `10.20.0.0/16` and `10.10.0.0/16` routes through `enp4s0`. Pinning the metrics is a
follow-up.

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
[Access Switch → Rollback](/docs/runbook/substrate/recovery/console-recovery/access-switch/#rollback). The
configuration is kept.

---

## Outcome

Done on 2026-09-16, in one operator window.

**Upload and reboot.** The operator reached the builder over the travel router and uploaded
the `.bin` through the tunnel. The "reboot using the backup image" box was **checked**, which
departs from the procedure: the switch rebooted straight after the write, not at a separately
chosen moment. It did no harm. The switch came up on 1.20.24 in `image1.bin`, replacing the
factory 1.1.3, and set `image1.bin` as **Next Startup Image** too, so the Boot Config step was
already done. `image2.bin` still holds 1.20.1. The link was down from 08:15:32 to 08:17:11 EDT.

**Verification.**

| Check | Result |
|---|---|
| Version and image slots | `1.20.24 Build 20260509 Rel.23533`. Current and next startup: `image1.bin` (1.20.24). Backup: `image2.bin` (1.20.1). |
| Ansible connects | Yes. The legacy SSH settings still work on 1.20.24. |
| STP | `Spanning tree is disabled`, the same as the baseline |
| LLDP | **`Enabled`**; the baseline was `Disabled`. The 1.20.4 default came up under an unchanged config, as expected. **Kept on** deliberately, for mapping neighbours port by port, and declared as `switch_lldp: true` (net #21, inventory #33). With the declaration in place, `--tags mgmt` finds the switch already matching and changes nothing. |
| Running config | No capture was taken before the upgrade, so it was checked against inventory instead. Every declared VLAN name, all four trunks (untagged, tagged and PVID), all four access ports, the hostname, the management address and the default gateway match. The undeclared ports are at defaults. |
| Reachability | The switch, OPNsense, the AP, both hypervisors, the Omada controller, the MQTT broker (`10.20.35.20`, through a tagged trunk) and the gateways of VLANs 10, 25, 30 and 35 answered. The IoT Pis did not, because their ports `gi1/0/3` and `gi1/0/14` have no link: nothing is plugged in or powered. |
| `switch-vlans.yml` | **Failed twice, then passed twice.** The first two runs, about 10 to 15 minutes after boot, each hit a 30-second command timeout near the end of the VLAN commands (`name blackhole`, then `vlan 999`). The next two runs, one with `-vvvv` and one at normal speed (66 s), finished with `failed=0`. The running config was identical before and after all four runs, and startup matches running. The command grammar still parses on 1.20.24. The timeout is recorded as intermittent: the switch may have still been settling after boot, but that isn't established. |

**No re-provisioning was needed.** The configuration survived the upgrade unchanged, and the
playbook runs applied nothing that wasn't already there.

**Noticed in the running config.** With no capture from before the upgrade, none of these can be
attributed to the new firmware:
- `telnet enable` is set.
- NTP is still at factory values: `system-time ntp UTC+08:00` with two public servers. The switch
  clock read about 12 hours ahead of the builder.
- `gi1/0/5` has a link but isn't declared in inventory, so whatever is on it is in VLAN 1, which
  isn't routed.
- `gi1/0/13` and `gi1/0/16` carry `no switchport general allowed vlan 1`. The other declared ports
  keep their default VLAN 1 membership. Inventory says nothing either way.

## Follow-ups

- [ ] Confirm whether 1.20.17 and later force a password change at first login after a reset.
  That can only be seen when the switch is reset, which the eventual adoption change will do.
- [ ] Move the switch firmware procedure into Lifecycle. It sits in the console-recovery page
  today.
- [ ] Merge net #21 and inventory #33, which declare LLDP.
- [ ] Pin the builder's route metrics (for example `enp4s0` 100, `enp1s0` 200), so the switch path
  wins again after an outage.
- [ ] Find the cause of the intermittent `switch-vlans.yml` command timeouts seen shortly after boot.
- [ ] Decide on `telnet enable`. If it goes, declare it.
- [ ] Set the switch's NTP servers and time zone from inventory.
- [ ] Identify what is on `gi1/0/5`, and declare the port or unplug it.
- [ ] Make VLAN 1 membership consistent across declared ports, and declare it.
- [ ] Before the next switch change, take the CLI captures. This change had to verify against
  inventory, because there was no capture to compare with.
