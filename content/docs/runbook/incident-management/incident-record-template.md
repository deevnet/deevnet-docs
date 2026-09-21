---
title: "Incident Record Template (INC)"
weight: 1
---

# Incident Record Template (INC)

The shape every [incident record](/docs/incidents/) takes. Copy the skeleton below into
`content/docs/incidents/<YYYY>/<NNNN>-<slug>.md`, numbered with the next unused `INC-NNNN` —
global across years and never reused, like ADRs.
[INC-0001: Firewall Policy Deleted, Total Connectivity Loss](/docs/incidents/2026/0001-firewall-policy-deletion/)
is a worked example.

Start the record while the incident is fresh, even with most sections empty. The timeline
and the wrong turns are the parts memory loses first.

---

## Skeleton

````markdown
---
title: "INC-NNNN: <What broke>"
weight: NNNN
---

# INC-NNNN: <What broke>

| | |
|---|---|
| **Date** | YYYY-MM-DD — the day it began |
| **Site** | |
| **Systems** | Devices, hosts and roles involved, by inventory name |
| **Severity** | What was lost, and what recovery required |
| **Status** | Open · Triage / Investigating / Mitigated / Remediated / Hardening — or Closed · Completed YYYY-MM-DD. See [Status](/docs/runbook/incident-management/#status) |
| **Times** | Timezone used in this record |

---

## Summary

What happened and why, in two short paragraphs.

## Impact

What stopped working, for whom, and for how long.

-

## Detection

How the incident was noticed, by what or by whom, and how long that took. If it was not
detected, say why not.

## Timeline

| Time | Event |
|---|---|
| | |

## Symptoms

What was observable, in the order it appeared: output, errors, what answered and what did not.

-

## Investigation

How the cause was found, including the wrong conclusions and what overturned them.

## Root cause

The fault, or the faults that combined. Cite the file and line.

## Recovery

How service came back, and the state things were left in.

## Contributing factors

What made it possible, worse, or harder to see — without being the cause.

-

## Corrective actions

Fix the faults behind this incident.

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | | | {{</* action-status "Open" */>}} |

## Preventive actions

Stop this class of failure recurring, here or elsewhere, or make surviving it unnecessary.

| # | Action | Where | Status |
|---|--------|-------|--------|
| | | | {{</* action-status "Open" */>}} |

## Follow-ups

Worth doing because of this incident, but fixing nothing in it. Status is Open, Scheduled, Done or
Declined; a Scheduled follow-up links to what carries it.

| # | Follow-up | Where | Status |
|---|-----------|-------|--------|
| | | | {{</* action-status "Open" */>}} |

## Lessons learned

What to carry into the next change, stated so it applies beyond this one incident.

-

## Related changes

The change that caused it, if any; changes made in the same window; the changes that fixed it.

-

## Related runbooks

Procedures used during recovery, and procedures written or changed because of it.

-
````

---

## Filling it in

- **Detection and symptoms are different things.** Detection is *how the incident came to
  light*, and how long that took. Symptoms are *what could be seen*, whether or not anyone read
  it correctly at the time. An incident that was visible but misread is recorded in both.
- **Corrective actions and preventive actions are different things.** Corrective actions fix
  the faults that caused this incident. Preventive actions stop the same class of failure
  elsewhere, or make surviving it unnecessary. Number actions across both tables, so that "action
  4" means one thing wherever it is cited.
- **Keep action status current.** Actions are Open, In Progress, Done or Declined; follow-ups
  are Open, Scheduled, Done or Declined — see [Actions and follow-ups](/docs/runbook/incident-management/#actions-and-follow-ups).
  Mark an action Done with the commit or PR that did it, or Declined with the reason. The
  incident closes when every action is Done or Declined and every follow-up is at least
  Scheduled, with a link. Until
  every action is done, the record's status says so. Move the substatus as actions land, and
  update the row on both index pages in the same commit.
- **Keep the record, even when it is embarrassing.** A wrong conclusion committed to git during
  the incident belongs under Investigation, quoted, with what overturned it.
- **Evidence over recollection:** command output, recap counts, timestamps. Cite files and
  lines so the analysis stays checkable after the code moves on.
- **Link both ways.** If a change caused the incident, name it under Related Changes, and add
  the incident to that change record's header table.
