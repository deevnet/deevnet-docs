---
title: "CHG-0063: The Core Router's Untagged LAN Loses Its Flat-Network Address"
weight: -0063
---

# CHG-0063: The Core Router's Untagged LAN Loses Its Flat-Network Address

| | |
|---|---|
| **Date** | 2026-11-12 |
| **Change type** | Decommission |
| **Classification** | Routine |
| **Status** | Complete |
| **Window** | 2026-11-12; address cleared by 06:20 EST, after-change backup 06:27 EST |
| **Site** | mobile |
| **Systems** | dv02cor002p01 (`lan`, `re0`) |
| **Automation** | None for the change itself: no `deevnet.net` role sets an interface's IPv4, so it is a GUI step. `make backup-router` in `ansible-collection-deevnet.net` against `ansible-inventory-deevnet/mobile`, before and after |
| **Risk** | Low — `re0` is the parent of every VLAN, so changing the wrong setting on `lan` (disabling it rather than clearing its address) takes the whole site off the network |
| **Related changes** | [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/), [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/), [CHG-0061](/docs/changes/2026/0061-core-router-restore-rehearsal/) |
| **Related incidents** | None |
| **Related runbooks** | [Core Router console recovery](/docs/runbook/substrate/recovery/console-recovery/core-router/) |

---

## Summary

The core router's untagged `lan` interface still carries `192.168.10.1/23`, the address of the flat
network that [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) replaced with VLANs. Its
post-migration step to clear it was never done. Nothing uses it: the switch port to `re0` is a trunk
with native VLAN 999, so no untagged frame reaches `lan` in normal operation; Kea has no subnet for
it; and on 2026-11-12 the router's ARP table held no address in `192.168.10.0/23` but its own.
Recovery of the router is from its console and its management address `10.20.99.1`, not from the
untagged LAN.

After this change `lan` stays assigned and enabled, as the parent of every VLAN, with no IPv4
address.

## Goal

- `lan` (`re0`) is enabled, with IPv4 configuration type **None** and no address.
- Every VLAN interface keeps its address, and the core router answers at `10.20.99.1`.
- No route, rule or ARP entry for `192.168.10.0/23` remains on the router.
- Kea still hands out leases on its VLAN subnets.

## Scope

**In scope:** the IPv4 address on `lan`.
**Out of scope:** the `lan` assignment itself and `re0`, which every VLAN rides on; the anti-lockout
rule; the Kea reservation `192.168.10.20` (`vyos-rt01`), tracked in the
[Reconciliation plan](/docs/roadmap/infrastructure/substrate/reconciliation/plan/), which turned out
to be gone already (see Outcome).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| `lan` disabled instead of its address cleared, taking every VLAN down | core router GUI | Change only **IPv4 Configuration Type**; leave **Enable** ticked. Console recovery if it happens |
| Kea fails on an interface with no address | Kea DHCPv4 | Kea already listens on `blackhole` (`opt9`), which has no address, and serves every subnet |
| Something still uses `192.168.10.0/23` | untagged LAN | ARP on 2026-11-12 shows only the router; the switch's native VLAN on `re0` is 999 |

## Prerequisites

- [ ] Backups taken: `make backup-router`, sealed into the inventory
- [ ] Console access to dv02cor002p01 (Mini DisplayPort monitor, USB keyboard)
- [ ] Vault decrypted, collections built

## Procedure

### Step 1: Back up the router

Not disruptive.

**Run:**

```bash
cd ansible-collection-deevnet.net && make backup-router
```

**Verify:**

1. The file it names is staged in `ansible-inventory-deevnet/backups/mobile/dv02cor002p01/`.

**Undo:** none needed.

### Step 2: Clear the address on `lan`

Disruptive only if done wrong; nothing uses the address.

**Run:** in the core router's GUI, **Interfaces → [LAN]**: set **IPv4 Configuration Type** to
**None**, leave **Enable** ticked, **Save**, then **Apply changes**.

**Verify:**

1. `ping -c1 10.20.99.1` answers, from management and from trusted.
2. The read-only interface audit shows `lan` with no address and every VLAN with its own.
3. A Wi-Fi client on trusted gets a lease and reaches the internet.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: Back up the router again

**Run:** `make backup-router`, and commit both backups through an inventory pull request.

## Verification

Every item under **Goal** holds, checked from clients and the router's API, not from Ansible.

## Undo

### Undo Step 2

In the GUI, **Interfaces → [LAN]**: **IPv4 Configuration Type** back to **Static IPv4**, address
`192.168.10.1/23`, **Save**, **Apply changes**. If the GUI is unreachable, restore the Step 1 backup
from the console, as rehearsed in [CHG-0061](/docs/changes/2026/0061-core-router-restore-rehearsal/).

## To close

**This change closes when every item below is done.** One line each: the steps and the check.

- [x] Step 1: router backed up (the 2026-11-11 backup; see Departures)
- [x] Step 2: address cleared on `lan`
- [x] Step 3: router backed up again
- [x] Verification: Goal holds from clients and the router's API

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| 2026-11-12 | 2 | The owner set `lan`'s IPv4 Configuration Type to None in the GUI, with the interface left enabled. |
| 2026-11-12 | Verification | From the router's API: `lan` enabled with no address; 10 of 11 `opt` interfaces addressed, the eleventh being `blackhole`, which has none by design; management `10.20.99.1/24`. ARP: 30 entries, none in `192.168.10.0/23`. Kea: 8 leases held. From the control host on management: the GUI on `10.20.99.1` answers 443, and the router routes to `10.20.10.1` and `10.20.25.1`. |
| 2026-11-12 | Verification | Kea's 15 reservations include none for `BC:24:11:2E:26:4E`, `192.168.10.20` or `vyos-rt01`: the orphan the Reconciliation plan listed was already gone. |
| 2026-11-12 | 3 | `make backup-router` sealed the after-change configuration into the inventory, staged with the owner's open inventory work. |

### Departures from the plan

- **No fresh backup before Step 2.** The router's last backup, from 2026-11-11, is the pre-change
  state; nothing else changed on the router in between.
- **Ping to `10.20.99.1` from management does not answer, and did not before.** The router's log
  shows it blocked by the default deny: since [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)
  management reaches the router itself on 443 and 22 only. Verification used 443 instead.

## Follow-ups

- [x] [Core Router console recovery](/docs/runbook/substrate/recovery/console-recovery/core-router/)
  checked the router with `ping -c1 10.20.99.1`, which the zone policy blocks from management.
  It and five other runbook pages now check ARP or the router's port 443 instead.
