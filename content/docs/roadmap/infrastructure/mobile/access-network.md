---
title: "Access Network"
weight: 8
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 3
---

# Access Network

How hosts and operators physically attach to the site's access switch, starting with a tidier
management path.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

The management segment (VLAN 99) should be easy to plug into, both for hosts and for an operator at
the rack, without weakening the segmentation or the recovery paths built on it.

**In Scope**
- Management access ports on the access switch `dv02acc001p01`
- Whether and how an extra switch may extend the management segment

**Out of Scope**
- Adopting the access switch into Omada, which ADR-0009 decides. This project only times its
  changes to that adoption.
- The zone policy between segments ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/))

---

## Considered: a dumb switch as a management backbone

The idea, raised on 2026-09-15: hang an unmanaged switch off a VLAN 99 port and plug the AP, the
Builder and the core router into it.

**Current attachment:** from `host_vars/dv02acc001p01.yml`.

| Device | Port | Mode |
|---|---|---|
| Core router `dv02cor002p01` | `gi1/0/1` | Trunk, native 999, all VLANs tagged. Management (10.20.99.1) is tagged too. |
| AP `dv02wap001p01` | `gi1/0/4` | Trunk, native 99, VLANs 10, 30, 31, 40 tagged |
| Builder `dv00bld001p01` | `gi1/0/16` | Access, VLAN 99 |
| Operator laptop | `gi1/0/2` | Access, VLAN 99 |

**The router and the AP can't sit behind a dumb switch on an access port.** An access port carries
one VLAN, untagged.
- **Router:** every interface it has is tagged, so all segments would lose their gateway,
  management included.
- **AP:** its SSIDs on VLANs 10, 30, 31 and 40 would go dark.

**Making that uplink a trunk doesn't fix it:**
- **One native VLAN:** a trunk has a single native VLAN. The router wants none (999), and the
  Builder needs untagged 99.
- **No isolation:** an unmanaged switch isolates nothing. Every port on it can tag its way onto any
  VLAN, which bypasses the per-port policy the zone policy relies on.
- **No loop protection:** it runs no spanning tree. One stray cable loops the network, and the
  router, AP and Builder go down together.
- **Invisible to the controller:** it can't be seen or managed there.

Whether a particular unmanaged switch forwards tagged frames at all depends on the model. That's an
inference, not a vendor statement.

**What works instead:**
- **Preferred: use the managed switch's free ports.**
  - The SG2218 has 16 RJ45 ports, and `gi1/0/5`–`gi1/0/12` are not declared. Undeclared ports sit
    on untagged VLAN 1, which isn't routed.
  - The claim that `gi1/0/2` is the only spare management port is only true because nothing else is
    declared.
  - A labeled block of VLAN 99 access ports gives the tidier path with no new hardware, no single
    point of failure, and the switch's own loop protection.
- **Acceptable for cable reach:** a dumb switch on a VLAN 99 access port, carrying untagged
  management devices only. The router and the AP stay on their own trunk ports.

---

## Management access ports ⏳

- ⏳ Declare a labeled block of free SG2218 ports as access VLAN 99. Do it as a port profile when the
  switch is adopted into Omada ([ADR-0009](/docs/architecture/decisions/0009-network-device-config-ownership/),
  after [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) and
  [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/)). Doing it first through
  `switch_vlans` would only be redone at adoption.
- ⏳ Update the inventory comment on `gi1/0/2`, and the console-recovery pages
  ([index](/docs/runbook/recovery/console-recovery/),
  [wireless AP](/docs/runbook/recovery/console-recovery/wireless-ap/),
  [access switch](/docs/runbook/recovery/console-recovery/access-switch/)), which call it the only
  spare management port.
- ⏳ If a dumb switch is ever added for cable reach: untagged VLAN 99 devices only; the core router and
  the AP stay on their own trunk ports; declare its uplink port with a description that says what
  is behind it.
