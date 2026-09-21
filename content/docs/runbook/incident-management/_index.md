---
title: "Incident Management"
weight: 7
bookCollapseSection: true
---

# Incident Management

How an incident on Deevnet infrastructure is recorded and followed through. The records
themselves are under [Incident Records](/docs/incidents/). This page and the
[incident record template](incident-record-template/) are how to write one.

An incident is any unplanned loss or degradation of service on a site, including one caused
by a change. The incident gets its own record even when the change already has one: the change
record says what was intended, and the incident record says what it cost and why.

---

## The record

Each incident gets one page, following the [template](incident-record-template/). The sections
follow the incident-handling lifecycle — detect, analyse, contain and recover, then learn — as
set out in NIST's incident-handling guidance (SP 800-61):

| Stage | Sections |
|---|---|
| What happened | Summary, Impact |
| Detection and analysis | Detection, Timeline, Symptoms, Investigation, Root Cause |
| Recovery | Recovery |
| After the incident | Contributing Factors, Corrective Actions, Preventive Actions, Lessons Learned |
| Links | Related Changes, Related Runbooks |

## Status

An incident carries a **status** and a **substatus**. The status says whether anything is left
to do; the substatus says how far along it is. The substatus moves forward only.

| Status | Substatus | Means |
|---|---|---|
| **Open** | **Triage** | Just recorded. Impact and severity are being established; nobody is yet sure what broke. |
| **Open** | **Investigating** | The fault is being looked for. Service may still be down. |
| **Open** | **Mitigated** | Service is restored, but the cause is not fixed — a reboot, a revert, a workaround. It can happen again. |
| **Open** | **Remediated** | The cause is fixed. Preventive actions are not yet chosen or not yet started. |
| **Open** | **Hardening** | Every corrective action is done. Only preventive actions or follow-ups remain. |
| **Closed** | **Completed** | Every action is done, or explicitly declined with the reason written down. Give the date. |

A record may skip a substatus — an incident whose cause is found and fixed in one move goes
straight from Investigating to Remediated — but it never moves back. If a closed incident's fix
turns out not to have worked, open a new incident and link the old one.

On the [Incident Records](/docs/incidents/) index the substatus is a coloured badge, written
`{{</* inc-status "Mitigated" */>}}`. The colour follows from the substatus and says how exposed
the site still is: **red** for Triage and Investigating (cause unknown, service may be down),
**orange** for Mitigated (service back, cause not fixed, so it can recur), **green** from
Remediated onward (cause fixed, only prevention left). An unknown substatus fails the build.

The record's header **Status** row leads with both words, for example
*"Open · Mitigated. Service restored by a guest reboot; root cause not established."*

## Writing one

- **Number and file name:** the next unused `INC-NNNN`, global and never reused, like ADRs.
  The file is `content/docs/incidents/<YYYY>/<NNNN>-<short-slug>.md`, with weight `NNNN`.
- **Title:** the date and what broke, from the operator's point of view — not the fix.
- **Add a row** to [Incident Records](/docs/incidents/) and to that year's page.
- **Keep the index current.** Whenever an incident is worked on — an action lands, the substatus
  moves, it closes — update its row on **both** index pages in the same commit as the record.
  The index is what gets read; a record that has moved on while its row has not is the index
  lying.
- **Actions carry a status, and it is kept current.** A record whose actions are all "Open" is
  a warning, not a resolution; say so plainly rather than implying the problem is behind you.
  When an action lands, mark it done with the commit or PR that did it.
- **Record the wrong conclusions too.** The mistaken diagnosis reached during an incident is
  usually more instructive than the correct one reached afterwards, and it is the part that
  gets quietly dropped. It belongs under Investigation.

Prefer evidence over recollection: command output, recap counts, timestamps. Cite the file and
line where a fault lives, so the analysis stays checkable after the code moves on.
