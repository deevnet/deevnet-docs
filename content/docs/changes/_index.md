---
title: "🔀 Change Records"
weight: 5
bookCollapseSection: true
aliases:
  - /docs/migrations/
---

# Change Records

One record per significant change to a site: what was changed and why, the end state it
aimed for, the procedure, how to undo it, and what actually happened.

The [runbook](/docs/runbook/) and these records hold different kinds of information. The
runbook is **maintained**: procedures and templates, kept current, and edited whenever
reality changes. A change record is **retained**: evidence of a change made on a given day.
It is written once and then left alone, apart from follow-ups closing. Incidents are kept
the same way, under [Incident Records](/docs/incidents/).

New records start from the [change record template](/docs/runbook/change-management/change-record-template/).
[Change Management](/docs/runbook/change-management/) says when a change needs one.

---

## Records

| ID | Date | Change | Type | Site | Status |
|---|---|---|---|---|---|
| CHG-0001 | 2026-03-21 | [Flat Network → VLANs](2026/0001-flat-network-to-vlans/) | Migration | mobile | Complete |
| CHG-0002 | 2026-03-26 | [Authority Transition Rework](2026/0002-authority-transition-rework/) | Configuration | mobile | Complete |
| CHG-0003 | 2026-09-05 | [Host Rename (ADR-0008)](2026/0003-host-rename/) | Migration | mobile | Complete |

Records are numbered `CHG-NNNN` in the order they are opened, like
[ADRs](/docs/architecture/decisions/): the number is global, never reused, and is how a record
is cited. They are grouped by year, and each carries the date execution started.

## Retrospective records

Changes made before this section existed are written up **retrospectively**. Each one is
rebuilt from the plan that drove the change, the automation logs, and git history, and says
so at the top. A retrospective record reshapes what was captured at the time. Where the
original material is silent, the record says so rather than filling the gap.
