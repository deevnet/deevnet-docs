---
title: "Hardware Evaluation"
weight: 1
aliases:
  - /docs/platforms/hardware-certification/
  - /docs/policies/lifecycle-management/certification/hardware-certification/
---

# Hardware Evaluation

How a model of hardware is evaluated for a role. For a model in service, the record is its own page
under [Hardware](/docs/platforms/hardware/). For a candidate, it is under
[Evaluations → Hardware](/docs/platforms/evaluations/hardware/) until it is selected.

---

## What is evaluated

A **model at a hardware revision, for a role**. The same model in a different role, or at a different
hardware revision, is a separate evaluation. Hardware revisions do change what a board carries,
such as the NIC chipset.

It is evaluated **with the software it will run**: the OS and driver are part of what is tested,
because a NIC's maturity depends on the driver. The record names the software it was tested with.
That software's own evaluation is separate ([Software Evaluation](/docs/policies/lifecycle-management/evaluation/software-evaluation/)).

---

## Criteria

Each criterion is checked and recorded as passed, failed, not tested or not applicable, with what
was done and what was seen. How the columns work is in [Evaluation](/docs/policies/lifecycle-management/evaluation/#how-the-criteria-are-written).

| # | Criterion | Level | Passes when | How to check |
|---|---|---|---|---|
| H1 | **Unattended install** | Required | The OS goes on from the site's own artifacts (network boot, an unattended installer, or a pre-imaged disk) with no step beyond choosing the boot device | Install it twice from the artifact server with the upstream unplugged. Both come up identical and reachable |
| H2 | **Console access** | Required | A local console, BIOS or recovery interface can be reached with the network down, using only the cables and adapters in the kit | Reach the login prompt and the BIOS with the kit alone, and write the route down as a console-recovery page |
| H3 | **Recovery from factory state** | Required | After a factory reset, it returns to service from code and a written procedure | Reset it on the bench and rebuild it with the automation. Record how long it took and every manual step |
| H4 | **NIC and driver** | Required | The NIC chipset is identified. On the chosen OS and driver, a 24-hour soak logs **no** link resets, watchdog timeouts or driver errors, and holds at least **90%** of line rate | Run `iperf3` in both directions for 24 hours through every port the role uses, then read the kernel or system log |
| H5 | **Management from code** | Required for network devices | The automation configures it through an API or CLI, and a second run changes nothing | Apply the role's configuration twice. The second run reports no changes |
| H6 | **Offline firmware upgrade** | Required | Firmware and BIOS upgrade from a file on the artifact server, with no internet. The rollback path is known, or the upgrade is declared irreversible | Upgrade on the bench from the mirrored file with the upstream unplugged |
| H7 | **Power** | Required | It runs from the kit's power. After power is pulled, it comes back on by itself, in the same configuration | Measure the draw at idle and under load. Pull the power **three** times |
| H8 | **Thermals** | Required | No thermal throttling or thermal shutdown through **4 hours** of sustained load, inside the case it will live in | A stress tool, or the role's own load, for 4 hours while reading the sensors and the kernel log |
| H9 | **Remote power-on** | Preferred | It can be woken over the network (Wake-on-LAN) from the site's router | Wake it from soft-off |
| H10 | **Role minimums** | Required | It meets every minimum its role's page states: ports, NICs, RAM, storage | Compare the spec sheet and the running system with the role page |
| H11 | **Longevity** | Required | The vendor has shipped a firmware update in the last **24 months**, and the model can still be bought or a spare is held | The vendor's download page, and a retailer or the spares shelf |

**Where these came from.** H4 is [INC-0004](/docs/incidents/2026/0004-core-router-lost/), a Realtek
NIC that timed out in service. H2 and H3 are the switch and AP, which have no console and are
recovered by factory reset ([Resiliency](/docs/policies/risk-management/resiliency/)). H6 is the
AP's firmware chain, one step of which could not be undone
([CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/)).

---

## Process

1. **Open the record.** Create the item if it's new, and a revision page for this evaluation, with the
   verdict *Under evaluation*.
2. **Evaluate on the bench**, against every criterion, with the software named in the record. Nothing
   in service depends on it yet.
3. **Record the evidence.** For each criterion: the result, what was tested, how, and what was seen.
4. **Set the verdict.** The operator decides. *Approved with conditions* names each Required criterion
   it misses or couldn't test, and what would clear it.
5. **Update the item page**: its current verdict, and the new row in its revisions table.
6. **Select it.** Only an approved model becomes a selection on its role's page. A candidate's page
   moves from Evaluations to Hardware when it is selected, and keeps its revisions.

A rejection is kept like an approval. The next evaluation of that model starts from what is already
known.
