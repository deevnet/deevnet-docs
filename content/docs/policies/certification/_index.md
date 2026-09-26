---
title: "Certification"
weight: 4
bookCollapseSection: true
---

# Certification

What a piece of hardware or software must demonstrate before Deevnet relies on it, so that a
selection means "tested against the criteria", not "it seemed fine".

Several limits Deevnet lives with were discovered in service rather than before purchase: a NIC
driver that watchdog-times out under load
([INC-0004](/docs/incidents/2026/0004-core-router-lost/)), devices with no out-of-band management
([Resiliency](/docs/policies/risk-management/resiliency/)), and an object store whose community
edition was archived while in use ([ADR-0026](/docs/architecture/decisions/0026-object-storage/)).
Certification moves those discoveries to before the thing is relied on.

This section is the **process**. The certifications themselves are records, kept under
[Implementation & Tooling → Certification](/docs/platforms/certification/), beside the selections
they qualify.

---

## What needs certifying

| Kind | What is certified | Process |
|---|---|---|
| **Hardware** | A model at a hardware revision, for a role (e.g. the SG2218 at hardware 1.20, as the access switch) | [Hardware Certification](hardware-certification/) |
| **Software** | A **release line** of a product, for a role (e.g. OPNsense 26.7, as the core router). Device firmware is software. | [Software Certification](software-certification/) |

**A release line, not every version.** A certification covers a major or minor line: OPNsense 26.7,
Proxmox VE 9, Grafana 13. Patch releases within the line inherit it, unless their release notes
change something a criterion depends on. Then the patch gets a dated addendum on the line's record.
The versions actually running are in the [Software Catalog](/docs/platforms/software-catalog/).

**When a certification is required:**
- before new hardware is selected on a platform page
- before a change moves something to a release line that isn't certified. The change record cites
  the certification.

**Everything in service before this policy existed** is *Not yet certified*. It is not blocked. It
is certified the next time it changes line, or sooner if the operator chooses.

---

## Verdicts

| Verdict | Meaning |
|---|---|
| {{< status-badge "evaluating" "Under evaluation" >}} | Being tested. Not yet usable as a selection. |
| {{< status-badge "complete" "Certified" >}} | Meets every criterion for the role. |
| {{< status-badge "active" "Certified with conditions" >}} | Usable for the role, with named conditions or accepted gaps. Each condition says what would clear it. |
| {{< status-badge "deprecated" "Not certified" >}} | Failed a criterion. Kept, so it isn't re-evaluated from scratch. |
| {{< status-badge "deprecated" "Superseded" >}} | A later certification of the same item replaced it. |
| {{< status-badge "deprecated" "Withdrawn" >}} | Was certified, then found wanting in service. Cites the incident or finding. |
| {{< status-badge "planned" "Not yet certified" >}} | In service from before this policy, or selected and not yet evaluated. |

The operator decides the verdict.

---

## How the records are organised

Records are **by item, not by date**, so a reader finds a thing by what it is, and its history
doesn't get in the way.

```text
Implementation & Tooling
└── Certification
    ├── Hardware
    │   └── <layer>                      Network · Management Plane · Tenant Compute
    │       └── <item>                   the model: current verdict, and a table of revisions
    │           └── <revision>           one evaluation, e.g. 2026-10 · hardware 1.20
    └── Software
        └── <layer>
            └── <item>                   the product: certified lines, and a table of revisions
                └── <release line>       one line, e.g. 26.7
```

- **The item page** is the only page that changes. It shows the current verdict and a table of
  every revision, newest first.
- **A revision page is a record.** Once its verdict is set, it isn't edited, except for:
  - a dated addendum at the end, such as a patch release that needed re-checking
  - a status note at the top when it is Superseded or Withdrawn
- **A revision is collapsed** in the sidebar under its item, so the navigation shows items, and a
  revision is one click deeper.

The shape of both pages is the [Certification Record Template](certification-record-template/).
