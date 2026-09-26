---
title: "Hardware Certification"
weight: 1
aliases:
  - /docs/platforms/hardware-certification/
---

# Hardware Certification

How a model of hardware is certified for a role. The records are under
[Certification → Hardware](/docs/platforms/certification/hardware/).

---

## What is certified

A **model at a hardware revision, for a role**. The same model in a different role, or at a different
hardware revision, is a separate certification. Hardware revisions do change what a board carries,
such as the NIC chipset.

It is evaluated **with the software it will run**: the OS and driver are part of what is tested,
because a NIC's maturity depends on the driver. The record names the software it was tested with.
That software's own certification is separate ([Software Certification](/docs/policies/lifecycle-management/certification/software-certification/)).

---

## Criteria

*Draft. Each area is checked, and the record says what was done and what was seen.*

| Area | What is checked |
|---|---|
| **Automated install** | PXE or unattended install; no manual step the build cannot reproduce |
| **Recovery** | Console access, which cable, and whether it survives a factory reset from code |
| **Network** | NIC chipset and driver maturity on the chosen OS; sustained throughput without errors |
| **Management** | An API or CLI the automation can drive; firmware upgrade path |
| **Power and thermals** | Draw, behavior on power loss, sustained load in the mobile case |
| **Longevity** | Vendor support window, firmware cadence, spare availability |

---

## Process

1. **Open the record.** Create the item if it's new, and a revision page for this evaluation, with the
   verdict *Under evaluation*.
2. **Evaluate on the bench**, against every criterion, with the software named in the record. Nothing
   in service depends on it yet.
3. **Record the evidence.** For each criterion: what was tested, how, and what was seen. A criterion
   that could not be tested is written as not tested, never as passed.
4. **Set the verdict.** The operator decides. *Certified with conditions* names each condition and
   what would clear it.
5. **Update the item page**: its current verdict, and the new row in its revisions table.
6. **Select it.** Only a certified model becomes a selection on its layer's platform page, which
   links to the certification.

A failure is kept like a pass. The next evaluation of that model starts from what is already known.
