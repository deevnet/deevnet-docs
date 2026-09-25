---
title: "CHG-0027: A Switch Port for dv02rpi004p01"
weight: 27
---

# CHG-0027: A Switch Port for dv02rpi004p01

| | |
|---|---|
| **Date** | 2026-09-25 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-09-25.** `Gi1/0/5` is an IoT access port, and `dv02rpi004p01` answers at its reservation `10.20.30.14`. Follow-ups cover the other three Pis. |
| **Window** | 2026-09-25, one `switch_vlans --tags access` run |
| **Site** | mobile |
| **Systems** | `dv02acc001p01` (switch port `Gi1/0/5`); `dv02rpi004p01` reached, not changed |
| **Automation** | `deevnet.net` `playbooks/switch-vlans.yml --tags access`; inventory `host_vars/dv02acc001p01.yml` (#57) |
| **Risk** | Low. One port that carried only this Pi. The run rewrites the other declared access ports with the configuration they already had |
| **Related changes** | None |
| **Related incidents** | None |
| **Related runbooks** | None |

---

## Summary

The operator reported a Pi in the rack, powered and cabled, but was unsure whether its OS was up.
None of the four inventory Pis (`10.20.30.11` to `.14`) answered anything, and no Pi MAC was on any
segment the Builder could reach. The switch told the story:

- `Gi1/0/5` had link at 1000M and had learned `dc:a6:32:c5:a1:a6`, which is
  **`dv02rpi004p01`**.
- The port was **undeclared** in the switch inventory, so it sat in untagged VLAN 1, the switch's
  default. VLAN 1 is not in `deevnet_vlans`, has no DHCP and is not routed. The Pi was up and
  transmitting, with nowhere to go.

## What was done

- **Declared `Gi1/0/5`** as an access port on VLAN 30, "dv02rpi004p01 iot", matching `Gi1/0/3` and
  `Gi1/0/14`.
- **Applied it** with `switch_vlans --tags access`, which saved the switch's configuration.

## Verification

- `show interface switchport gigabitEthernet 1/0/5`: PVID 30, VLAN 30 untagged.
- `10.20.30.14` (`dv02rpi004p01.mobile.deevnet.net`) answered within about 20 seconds, taking its
  DHCP reservation.
- What is on it:
  - **Ubuntu 23.10 (Mantic)**, identified by its SSH server (`OpenSSH_9.3p1 Ubuntu-1ubuntu3.6`);
  - SSH on 22, and nothing else open;
  - the Builder's `a_autoprov` key is refused.

  It is a hand-installed OS, not an image-factory card, and Ubuntu 23.10 has been end-of-life since
  July 2024.

### Departures

- As on the other access ports, the port stays a member of VLAN 1 untagged next to VLAN 30. The
  PVID is 30, so the Pi's traffic lands in IoT. The role never removes VLAN 1 from a port.

## Follow-ups: the rest of the Pi fleet

Switch and inventory state on 2026-09-25:

| Pi | MAC | Reservation | Switch port | Link | State |
|---|---|---|---|---|---|
| `dv02rpi001p01` (`sdr`) | `dc:a6:32:c3:b4:bc` | `10.20.30.11` | `Gi1/0/14` | **down** | not cabled or powered off |
| `dv02rpi002p01` | `dc:a6:32:c5:a0:c5` | `10.20.30.12` | `Gi1/0/3` | **down** | not cabled or powered off |
| `dv02rpi003p01` | `dc:a6:32:c5:a1:4d` | `10.20.30.13` | **none declared** | — | not seen on any port |
| `dv02rpi004p01` | `dc:a6:32:c5:a1:a6` | `10.20.30.14` | `Gi1/0/5` | up | **Ubuntu 23.10, EOL, no automation access** |

- [ ] **dv02rpi003p01 has no switch port.** Pick one (`Gi1/0/6` to `Gi1/0/12` are free) and declare
      it before cabling, or it too lands in VLAN 1.
- [ ] **dv02rpi001p01 and dv02rpi002p01:** check whether they're powered and cabled to `Gi1/0/14`
      and `Gi1/0/3`. Both ports have no link today.
- [ ] **dv02rpi004p01:** decide its purpose. It's the natural first **real-hardware test of the
      take-home `pi-backend` image** (flash from the tenant downloads' `pi/` and run the first-boot
      self-test). Otherwise, reimage it from the image factory so it has automation access and a
      supported OS.
- [ ] **Undeclared ports are a trap.** An undeclared port is live in VLAN 1, so a device plugged in
      there looks dead rather than refused. The standard wants unused ports in a blackhole VLAN
      (999). Declaring every unused port that way is a separate change.
