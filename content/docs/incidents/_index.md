---
title: "🚨 Incident Records"
weight: 6
bookCollapseSection: true
aliases:
  - /docs/runbook/rca/
---

# Incident Records

One record per incident on Deevnet infrastructure: what broke, how it was found, why it
happened, how service came back, and what was done so it does not happen again. Records are
numbered `INC-NNNN` in the order they are opened, like [ADRs](/docs/architecture/decisions/),
and grouped by year.

[Change Management](/docs/runbook/change-management/) states that *"manual changes without
validation are considered defects."* Most incidents are what happened when a change reached a
live site without the validation that would have caught it. Each record is written so the next
person meets the failure mode in a document rather than in the dark.

Like [Change Records](/docs/changes/), these are **retained** information: evidence, written
once, updated only as their actions close. How to write one, and the template, are **maintained**
in the runbook under [Incident Management](/docs/runbook/incident-management/).

---

## Records

| ID | Date | Incident | Site | Root cause | Actions |
|----|------|----------|------|-----------|---------|
| INC-0001 | 2026-09-07 | [Firewall Policy Deleted, Total Connectivity Loss](2026/0001-firewall-policy-deletion/) | mobile | Empty desired set treated as authoritative by an ungated reconcile | Done; 3 open items |
