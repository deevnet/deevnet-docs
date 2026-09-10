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

| Date | Change | Type | Site | Status |
|---|---|---|---|---|
| 2026-03-21 | [Flat Network → VLANs](2026/2026-03-21-flat-network-to-vlans/) | Migration | mobile | Complete |
| 2026-03-26 | [Authority Transition Rework](2026/2026-03-26-authority-transition-rework/) | Configuration | mobile | Complete |

Records are grouped by year and named `YYYY-MM-DD — <what changed>`, dated by the day
execution started.

## Retrospective records

Changes made before this section existed are written up **retrospectively**. Each one is
rebuilt from the plan that drove the change, the automation logs, and git history, and says
so at the top. A retrospective record reshapes what was captured at the time. Where the
original material is silent, the record says so rather than filling the gap.
