---
title: "Incident Management"
weight: 3
bookCollapseSection: true
---

# Incident Management

How to record an incident and keep its record current. What counts as an incident, what each status
means and when a record may close are set by the
[Incident Management](/docs/policies/incident-management/) policy.

To open a record, copy the [incident record template](incident-record-template/).

---

## The record

Each incident gets one page. Its sections follow the incident-handling lifecycle — detect, analyze,
contain and recover, then learn — as set out in NIST's incident-handling guidance (SP 800-61):

| Stage | Sections |
|---|---|
| What happened | Summary, Impact |
| Detection and analysis | Detection, Timeline, Symptoms, Investigation, Root Cause |
| Recovery | Recovery |
| After the incident | Contributing Factors, Corrective Actions, Preventive Actions, Follow-ups, Lessons Learned |
| Links | Related Changes, Related Runbooks |

---

## Writing one

- **Number and file name:** the next unused `INC-NNNN`, global and never reused, like ADRs.
  The file is `content/docs/incidents/<YYYY>/<NNNN>-<short-slug>.md`, with `weight: -NNNN` so the
  newest sorts first.
- **Title:** the date and what broke, from the operator's point of view — not the fix.
- **Add a row at the top** of [Incident Records](/docs/incidents/) and of that year's page.
- **Keep the index current.** Whenever an incident is worked on — an action lands, the substatus
  moves, it closes — update its row on **both** index pages in the same commit as the record.
- **The header's Status row** leads with both words, for example
  *"Open · Mitigated. Service restored by a guest reboot; root cause not established."*
- **Badges.** On the index the substatus is written `{{</* inc-status "Mitigated" */>}}`; in the
  action tables each row carries `{{</* action-status "Open" */>}}` followed by the commit, PR or date
  that settles it. An unknown value fails the build.
- **Record the wrong conclusions too.** The mistaken diagnosis reached during an incident is
  usually more instructive than the correct one reached afterwards, and it is the part that
  gets quietly dropped. It belongs under Investigation.

Prefer evidence over recollection: command output, recap counts, timestamps. Cite the file and
line where a fault lives, so the analysis stays checkable after the code moves on.
