---
title: "Incident Management"
weight: 10
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

## Writing one

- **File name:** `content/docs/incidents/<YYYY>/<YYYY-MM-DD>-<short-slug>.md`, with weight
  `YYYYMMDD`, so each year sorts chronologically.
- **Title:** the date and what broke, from the operator's point of view — not the fix.
- **Add a row** to [Incident Records](/docs/incidents/) and to that year's page.
- **Actions carry a status, and it is kept current.** A record whose actions are all "Open" is
  a warning, not a resolution; say so plainly rather than implying the problem is behind you.
  When an action lands, mark it done with the commit or PR that did it.
- **Record the wrong conclusions too.** The mistaken diagnosis reached during an incident is
  usually more instructive than the correct one reached afterwards, and it is the part that
  gets quietly dropped. It belongs under Investigation.

Prefer evidence over recollection: command output, recap counts, timestamps. Cite the file and
line where a fault lives, so the analysis stays checkable after the code moves on.
