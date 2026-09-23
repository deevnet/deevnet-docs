---
title: "Hardware Certification"
weight: 5
---

# Hardware Certification {{< status-badge "planned" "Planned" >}}

What a piece of hardware has to demonstrate before it is selected for a role — so that a selection
on these pages means "tested against the criteria", not "it seemed fine".

This page is a placeholder: the structure is set, the criteria are not yet written.

---

## Why

Several limits Deevnet lives with were discovered in service rather than before purchase — a NIC
driver that watchdog-times out under load
([INC-0004](/docs/incidents/2026/0004-core-router-lost/)), devices with no out-of-band management
([Resiliency](/docs/policies/risk-management/resiliency/)). Certification moves those discoveries
to before the hardware is relied on.

## Planned criteria

| Area | Examples of what would be checked |
|---|---|
| **Automated install** | PXE or unattended install; no manual step the build cannot reproduce |
| **Recovery** | console access, which cable, whether it survives a factory reset from code |
| **Network** | NIC chipset and driver maturity on the chosen OS; sustained throughput without errors |
| **Management** | an API or CLI the automation can drive; firmware upgrade path |
| **Power and thermals** | draw, behaviour on power loss, sustained load in the mobile case |
| **Longevity** | vendor support window, firmware cadence, spare availability |

## Planned process

1. Candidate evaluated on the bench against the criteria
2. Result recorded, pass or fail, with what was tested
3. Passing hardware becomes a selection on its layer's page; failures are kept, so they are not
   re-evaluated from scratch
