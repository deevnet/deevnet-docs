---
title: "🔀 Migrations"
weight: 5
bookCollapseSection: true
---

# Migrations

Major changes to a site, each written up as a change record: what was changed and why, the end
state it was aiming for, the procedure, how to undo it, and what actually happened.

The [runbook](/docs/runbook/) holds procedures you repeat. A migration is done once, so its
record lives here, dated by the day execution started. Runbook pages still link into these
records where a step is worth reusing.

Records for changes made before this section existed are **retrospective**. They were rebuilt
from the plan that drove the change, the automation logs, and git history. They reshape what
was captured at the time; they do not fill gaps with guesses.

---

## Records

| Date | Change | Site | Status |
|---|---|---|---|
| 2026-03-21 | [VLAN Migration](2026-03-21-vlan-migration/) — flat network to segmented VLANs | mobile | Complete |

---

## What a record contains

| Section | Answers |
|---|---|
| **Description and goal** | Why the change was made, and the end state that counts as done |
| **Scope and risk** | What it touches, what can break, and what guards against it |
| **Procedure** | The steps, in order, each with its own verification |
| **Undo** | How to back each step out, in reverse order, and where undo stops being possible |
| **Outcome** | What happened when it ran, and where that departed from the plan |
| **Issues and follow-ups** | Problems hit along the way, and work the change left open |
