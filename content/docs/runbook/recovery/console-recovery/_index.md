---
title: "Console Recovery"
weight: 1
bookCollapseSection: true
aliases:
  - /docs/runbook/console-recovery/
---

# Console Recovery

Getting back into an infrastructure device when the network can no longer reach it, and
returning it to declared state afterwards.

Every device in this section is managed *through* the network it helps provide. The core
router's management path is a rule on the core router; the switch's management address rides
the VLANs the switch defines; the hypervisors reach the world through a bridge they
configure themselves. That circularity is normal and mostly invisible — it matters only on
the day a change removes the path used to make changes. These pages are what you follow on
that day.

## By device

| Device | Address | Way in | Page |
|---|---|---|---|
| Core router `dv02cor002p01` | 10.20.99.1 | Mini DisplayPort + USB keyboard | [Core router](/docs/runbook/recovery/console-recovery/core-router/) |
| Hypervisors `dv02hyp001p01`, `dv02hyp002p02` | 10.20.99.21, .22 | DisplayPort→HDMI adapter + USB keyboard | [Hypervisor](/docs/runbook/recovery/console-recovery/hypervisor/) |
| Access switch `dv02acc001p01` | 10.20.99.10 | Factory reset, then reapply | [Access switch](/docs/runbook/recovery/console-recovery/access-switch/) |
| Access point `dv02wap001p01` | 10.20.99.9 | Wired into the switch first, then factory reset | [Wireless AP](/docs/runbook/recovery/console-recovery/wireless-ap/) |

## Two kinds of recovery

The router and the hypervisors are **repaired in place**. Both hold state that is expensive
or impossible to reconstruct — the router's configuration history, the hypervisors' running
VMs — so the console exists to fix the one thing that broke and leave the rest alone.

The switch and the AP are **reset and reapplied**. Their entire configuration is declared in
inventory and rebuilt by a playbook, so the fastest route back is usually to discard the
device's state rather than diagnose it. The cost is a bootstrap step: a factory-reset device
is not at its inventory address, so automation cannot reach it until you put it back on the
network by hand.

The AP adds one more, and it is the one that catches people out: **it is the path you would
normally use to reach everything else here.** Wireless management dies with it, so its
recovery begins by cabling into the access switch rather than by touching the AP at all — and
the management segment has no DHCP pool, so that laptop needs a hand-set address. Port
`gigabitEthernet 1/0/2` on the access switch is declared and held empty for this; see
[Wireless AP step 1](/docs/runbook/recovery/console-recovery/wireless-ap/).

## Keep findable

| Item | Needed for |
|---|---|
| Mini DisplayPort cable | Core router — unusual connector, only ever needed on the worst day |
| Patch cable + USB-Ethernet adapter | The AP — it carries the operator's own connectivity, so recovering it starts by going wired |
| DisplayPort→HDMI adapter | Hypervisors |
| USB keyboard | All console work |
| A monitor that is not on the affected network | All console work |

## Before you need any of this

Take a config backup before a disruptive change to the router: **System → Configuration →
Backups → Download**, as the
[segmentation prerequisites](/docs/changes/2026/0001-flat-network-to-vlans/prerequisites/) already
require. OPNsense keeps its own history on the box, which covers a configuration mistake but
not a failed disk, and there is no off-box backup automation in any collection.

For the switch and the AP there is nothing to back up — inventory is the backup.

## Related

- [Change Management](/docs/runbook/change-management/) — what actually validates a network change, and why `--check --diff` does not
- [CHG-0001 issues and follow-ups](/docs/changes/2026/0001-flat-network-to-vlans/troubleshooting/) — faults that are not lockouts, as met during segmentation
- [Incident Records](/docs/incidents/) — where these procedures came from
