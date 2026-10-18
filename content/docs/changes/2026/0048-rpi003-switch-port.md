---
title: "CHG-0048: A Switch Port for dv02rpi003p01"
weight: -48
---

# CHG-0048: A Switch Port for dv02rpi003p01

| | |
|---|---|
| **Date** | 2026-10-18 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-10-18.** `Gi1/0/11` is an IoT access port, and `dv02rpi003p01` answers at its reservation `10.20.30.13`. Its card is not an image-factory card. |
| **Window** | 2026-10-18, one `switch_vlans --tags access` run |
| **Site** | mobile |
| **Systems** | `dv02acc001p01` (switch port `Gi1/0/11`); `dv02rpi003p01` reached, not changed |
| **Automation** | `deevnet.net` `playbooks/switch-vlans.yml --tags access`; inventory `host_vars/dv02acc001p01.yml` |
| **Risk** | Low. One port that carried only this Pi. The run rewrites the other declared access ports with the configuration they already had |
| **Related changes** | [CHG-0027](../0027-rpi004-switch-port/), the same trap on `Gi1/0/5`, whose follow-up named this Pi |
| **Related incidents** | None |
| **Related runbooks** | None |

---

## Summary

The operator cabled `dv02rpi003p01` with a card of unknown origin and asked what was on it. It did
not answer at `10.20.30.13`, and `a_autoprov` timed out. The switch told the story, as it did for
`dv02rpi004p01` in [CHG-0027](../0027-rpi004-switch-port/):

- `show mac address-table address dc:a6:32:c5:a1:4d`: learned on **`Gi1/0/11`, VLAN 1**.
- `Gi1/0/11` was **undeclared**, so it sat in untagged VLAN 1: no DHCP, no route. CHG-0027 left
  "dv02rpi003p01 has no switch port" as a follow-up; it was cabled before one was declared.

## What was done

- **Declared `Gi1/0/11`** as an access port on VLAN 30, "dv02rpi003p01 iot", after `Gi1/0/5`.
- **Applied it** with `switch_vlans --tags access`, so the VLANs and trunks were not touched. The
  switch is `standalone`, so this was not a break-glass run.

## Verification

- `show interface switchport gigabitEthernet 1/0/11`: PVID 30, VLAN 30 untagged. VLAN 1 untagged
  stays a member, as on every access port; see CHG-0027's departures.
- `10.20.30.13` (`dv02rpi003p01.mobile.deevnet.net`) answered within seconds, taking its DHCP
  reservation.
- What is on it:
  - **Ubuntu 23.10 (Mantic)**, identified by its SSH server (`OpenSSH_9.3p1 Ubuntu-1ubuntu3.6`),
    the same as the card in `dv02rpi004p01`;
  - the Builder's `a_autoprov` key is refused (`publickey,password`).

  A hand-installed OS, not an image-factory card, and end-of-life since July 2024.

### Departures

- Carried out from the operator's Mac, through the Builder, by an assistant session. The inventory
  change is on branch `rpi003-switch-port` of `ansible-inventory-deevnet`.

## Follow-ups

- [ ] **dv02rpi003p01:** decide its purpose, and reimage it from the image factory so it has
      automation access and a supported OS. EdS's one-Pi back end (`pi-backend`) is a candidate.
- [ ] **Undeclared ports are still a trap:** `Gi1/0/6` to `Gi1/0/10` and `Gi1/0/12` are live in
      VLAN 1. CHG-0027's follow-up stands.
