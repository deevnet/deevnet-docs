---
title: "Change Management"
weight: 1
bookCollapseSection: true
aliases:
  - /docs/runbook/change-management/
---

# Change Management

How change is introduced into a site safely. This page sets the rules; how to follow them — change
types, the validation checklist and the record template — is
[Change Management](/docs/runbook/substrate/change-management/) in the runbook.

---

## Principles

- **Every change is validated before it is applied.** A manual change without validation is a
  defect.
- **Every change can be undone**, or says in its record why it cannot and what replaces an undo.
- **A secret a change creates is locked in before the change goes further**: encrypted, committed
  and pushed. Until then it exists in one place that nothing protects.
- **Inventory and code are the record of how the site is configured.** A change made by hand is
  either brought into code or recorded as an exception.

---

## Change Classification

| Class | Examples | Validation required |
|------|----------|-------------------|
| **Routine** | Package updates, config tweaks | Syntax check, dry run |
| **Structural** | New roles, playbook changes | Full test run |
| **Disruptive** | Network changes, storage migration | Staged rollout, backup, and a way back in if the change cuts off the path it was made over |

---

## Change Records

Every **disruptive** change gets a change record, opened before it runs. Structural and routine
changes may have one; otherwise their commit history is their record. Records are kept under
[Change Records](/docs/changes/), numbered `CHG-NNNN`, and are **retained**: written once, and
changed after the fact only to close their follow-ups.

**The index is kept current.** Opening a record, and every change to its date or status, updates the
index in the same commit as the record.

A change that goes wrong in a way that affects service also gets an incident record
([Incident Management](/docs/policies/incident-management/)).

---

## How validation is done today

Validation is manual, from the [runbook checklist](/docs/runbook/substrate/change-management/#validation-checklist).
Nothing runs it automatically yet; checks on every pull request are on the
[Patch Automation](/docs/roadmap/infrastructure/mobile/patch-automation/) roadmap.
