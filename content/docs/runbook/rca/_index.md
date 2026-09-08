---
title: "Incident RCAs"
weight: 10
bookCollapseSection: true
---

# Incident RCAs

Root cause analyses for incidents on Deevnet infrastructure. One page per incident.

[Change Management](/docs/runbook/change-management/) states that *"manual changes without
validation are considered defects."* These pages are the record of what happened when a
change reached a live site without the validation that would have caught it — written so
the next person meets the failure mode in a document rather than in the dark.

## Incidents

| Date | Incident | Site | Root cause | Actions |
|------|----------|------|-----------|---------|
| 2026-09-07 | [Firewall policy deleted, total connectivity loss](/docs/runbook/rca/2026-09-07-firewall-policy-deletion/) | mobile | Empty desired set treated as authoritative by an ungated reconcile | Open |

## Writing one

- **File name:** `YYYY-MM-DD-short-slug.md`, so the section sorts chronologically.
- **Title:** the date and what broke, from the operator's point of view — not the fix.
- **Add a row** to the table above, newest at the bottom.
- **Corrective actions carry a status.** An RCA whose actions are all "Open" is a warning,
  not a resolution; say so plainly rather than implying the problem is behind you.
- **Record the wrong conclusions too.** The mistaken diagnosis reached during an incident
  is usually more instructive than the correct one reached afterwards, and it is the part
  that gets quietly dropped.

Prefer evidence over recollection: command output, recap counts, timestamps. Cite the file
and line where a fault lives, so the analysis stays checkable after the code moves on.
