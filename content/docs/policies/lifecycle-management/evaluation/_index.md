---
title: "Evaluation"
weight: 1
bookCollapseSection: true
aliases:
  - /docs/policies/lifecycle-management/certification/
---

# Evaluation

What a piece of hardware or software must show before Deevnet relies on it, so that a selection
means "checked against the criteria", not "it seemed fine".

Several limits Deevnet lives with were discovered in service rather than before purchase: a NIC
driver that watchdog-times out under load
([INC-0004](/docs/incidents/2026/0004-core-router-lost/)), devices with no out-of-band management
([Resiliency](/docs/policies/risk-management/resiliency/)), and an object store whose community
edition was archived while in use ([ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/)).
Evaluation moves those discoveries to before the thing is relied on.

Evaluation is stages 2 and 6 of [Lifecycle Management](/docs/policies/lifecycle-management/):
the gate between choosing something and relying on it, passed again at every new line. It is an
operator's check against written criteria, not a formal certification.

This section is the **process**. The evaluations themselves are records: a hardware model's is
on its page under [Implementation & Tooling → Hardware](/docs/platforms/hardware/), beside its specs;
candidates not yet in service, and all software, are under
[Implementation & Tooling → Evaluations](/docs/platforms/evaluations/).

---

## What is evaluated

| Kind | What is evaluated | Criteria and process |
|---|---|---|
| **Hardware** | A model at a hardware revision, for a role (e.g. the SG2218 at hardware 1.20, as the access switch) | [Hardware Evaluation](hardware-evaluation/) |
| **Software** | A **release line** of a product, for a role (e.g. OPNsense 26.7, as the core router). Device firmware is software. | [Software Evaluation](software-evaluation/) |

**A release line, not every version.** An evaluation covers a major or minor line: OPNsense 26.7,
Proxmox VE 9, Grafana 13. Patch releases within the line inherit its approval, unless their release
notes change something a criterion depends on. Then the patch gets a dated addendum on the line's
record. The versions actually running are in the [Software Catalog](/docs/platforms/software-catalog/).

**When an evaluation is required:**
- before new hardware is selected on a platform page
- before a change moves something to a release line that isn't approved. The change record cites
  the evaluation.

**Everything in service before this policy existed** is *Not yet evaluated*. It is not blocked. It
is evaluated the next time it changes line, or sooner if the operator chooses.

---

## How the criteria are written

Each criterion on the hardware and software pages has:

- **Level.** *Required* criteria decide the verdict. *Preferred* criteria are recorded, and a miss
  is noted, but a miss alone never rejects.
- **Passes when.** A condition someone else could check and get the same answer. Numbers are
  thresholds, not targets.
- **How to check.** The test that shows it. A criterion that could not be tested is recorded as
  *not tested*, never as passed.

A criterion that doesn't apply to the role, such as management from code for a Pi, is recorded as
*not applicable*, with the reason.

---

## Verdicts

| Verdict | Meaning |
|---|---|
| {{< status-badge "evaluating" "Under evaluation" >}} | Being checked. Not yet usable as a selection. |
| {{< status-badge "complete" "Approved" >}} | Passes every Required criterion for the role. |
| {{< status-badge "active" "Approved with conditions" >}} | Usable for the role, with named Required criteria it misses or couldn't test. Each condition says what would clear it. |
| {{< status-badge "deprecated" "Rejected" >}} | Fails a Required criterion, and the miss isn't accepted. Kept, so it isn't re-evaluated from scratch. |
| {{< status-badge "deprecated" "Superseded" >}} | A later evaluation of the same item replaced it. |
| {{< status-badge "deprecated" "Withdrawn" >}} | Was approved, then found wanting in service. Cites the incident or finding. |
| {{< status-badge "planned" "Not yet evaluated" >}} | In service from before this policy, or a candidate not yet checked. |

The operator decides the verdict. *Approved with conditions* is how an accepted gap is recorded: it
is honest about the miss rather than lowering the criterion.

---

## How the records are organized

Records are **by item, not by date**, so a reader finds a thing by what it is, and its history
doesn't get in the way.

```text
Implementation & Tooling
├── Hardware
│   └── <group>                          Network · Compute
│       └── <item>                       the model in service: its specs, current verdict, and a table of revisions
│           └── <revision>               one evaluation, e.g. 2026-10 · hardware 1.20
└── Evaluations
    ├── Hardware
    │   └── <candidate>                  a model not yet in service; moves under Hardware once selected
    └── Software
        └── <layer>
            └── <item>                   the product: approved lines, and a table of revisions
                └── <release line>       one line, e.g. 26.7
```

- **The item page** is the only page that changes. It shows the current verdict and a table of
  every revision, newest first.
- **A revision page is a record.** Once its verdict is set, it isn't edited, except for:
  - a dated addendum at the end, such as a patch release that needed re-checking
  - a status note at the top when it is Superseded or Withdrawn
- **A revision is collapsed** in the sidebar under its item, so the navigation shows items, and a
  revision is one click deeper.

The shape of both pages is the [Evaluation Record Template](evaluation-record-template/).
