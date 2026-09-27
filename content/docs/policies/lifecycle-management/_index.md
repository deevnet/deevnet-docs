---
title: "Lifecycle Management"
weight: 4
bookCollapseSection: true
---

# Lifecycle Management

The life of a piece of hardware or software at Deevnet, from being chosen to being taken out of
service, and what has to be true at each stage. How to carry out each stage is in the runbook's
[Lifecycle](/docs/runbook/substrate/lifecycle/) section. This section says what each one requires.

---

## Stages

| Stage | What has to be true | Policy | Recorded in |
|---|---|---|---|
| **1. Select** | A need is met by a selection, with its rationale and alternatives | This section | Its [Implementation & Tooling](/docs/platforms/) page, or an [ADR](/docs/architecture/decisions/) |
| **2. Evaluate** | The selection is checked against the criteria before anything relies on it | [Evaluation](evaluation/) | Its [Hardware](/docs/platforms/hardware/) page, or [Evaluations](/docs/platforms/evaluations/) |
| **3. Deploy** | It goes in through a change that cites the evaluation | [Change Management](/docs/policies/change-management/) | A [change record](/docs/changes/), and the [Software Catalog](/docs/platforms/software-catalog/) |
| **4. Discover** | What is running is checked against the catalog, and each item's upstream is watched for releases, end of life and advisories. Each finding is triaged into one of the stages below | [Discovery](discovery/) | The catalog; findings in change records, evaluations or the risk register |
| **5. Patch** | It stays on an approved line. Patches are applied within the line, after their notes are read | [Vulnerability Management](/docs/policies/risk-management/vulnerability-management/), [Change Management](/docs/policies/change-management/) | Change records, and the catalog |
| **6. Upgrade** | A new line is evaluated and approved **before** the change that moves to it | [Evaluation](evaluation/), then [Change Management](/docs/policies/change-management/) | A new evaluation revision, then a change record of type Upgrade |
| **7. Retire** | It is removed through a change: its configuration, secrets, artifacts and records of it in inventory, not just stopped | [Change Management](/docs/policies/change-management/) | A change record (e.g. [CHG-0017](/docs/changes/2026/0017-retire-mosquitto/)); removed from the catalog; its evaluation marked Superseded |

Stages 2 and 6 are where evaluation sits. It is the gate between choosing something and relying
on it, and it is passed again each time the thing moves to a new line. Stage 4 is what notices that
a new line, a patch or an end of life has arrived.

---

## What tracks where an item is

- **In service, and at what version:** the [Software Catalog](/docs/platforms/software-catalog/),
  the system of record for versions.
- **Whether it was evaluated, and against what:** its evaluation record, on its [Hardware](/docs/platforms/hardware/) page or under [Evaluations](/docs/platforms/evaluations/).
- **How it got there, and every change since:** the [change records](/docs/changes/) that name it.

Everything in service today predates this section. It entered at stage 3 without stage 2, and is
*Not yet evaluated* until its next upgrade, or sooner.
