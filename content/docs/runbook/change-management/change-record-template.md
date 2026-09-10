---
title: "Change Record Template (CHG)"
weight: 1
---

# Change Record Template (CHG)

The shape every [change record](/docs/changes/) takes. Copy the skeleton below into a new file,
fill it in before the change runs, and complete **Outcome** after it has run.
[2026-03-21 — Flat Network → VLANs](/docs/changes/2026/2026-03-21-flat-network-to-vlans/) is a
worked example of a multi-phase change.

---

## Where it goes

| | |
|---|---|
| **Single-page change** | `content/docs/changes/<YYYY>/<YYYY-MM-DD>-<slug>.md` |
| **Multi-phase change** | A folder `content/docs/changes/<YYYY>/<YYYY-MM-DD>-<slug>/`. `_index.md` is the record; numbered phase pages hold the procedure; `undo.md` holds the undo; optionally `troubleshooting.md` holds issues and follow-ups. Add `bookCollapseSection: true` to `_index.md`. |
| **Title** | `YYYY-MM-DD — <What changed>`, from the site's point of view, e.g. "Flat Network → VLANs" |
| **Date** | The day execution starts. While the change is still *Planned*, use the planned date, and move it if the date moves. |
| **Weight** | `YYYYMMDD`, so records sort chronologically |
| **Index** | Add a row to [Change Records](/docs/changes/) and to that year's page |

## Status

`Planned` → `In progress` → `Complete`, or `Rolled back` or `Abandoned`.
A record is never deleted. A change that was abandoned or rolled back is exactly the one
worth keeping.

---

## Skeleton

````markdown
---
title: "YYYY-MM-DD — <What changed>"
weight: YYYYMMDD
---

# YYYY-MM-DD — <What changed>

| | |
|---|---|
| **Change type** | Migration · Upgrade · Configuration · Deployment · Decommission |
| **Classification** | Routine · Structural · Disruptive |
| **Status** | Planned · In progress · Complete · Rolled back · Abandoned |
| **Window** | Planned date and time; then the actual start and end |
| **Site** | |
| **Systems** | Hosts and services touched, by inventory name |
| **Automation** | Collection, playbooks or make targets, and the inventory they run against |
| **Risk** | Low · Medium · High — and the one thing most likely to go wrong |
| **Related incidents** | None |
| **Related runbooks** | |

---

## Summary

What is changing and why. What the site is like now, and what it will be like after.

## Goal

The end state that counts as done, as facts a command or a look can confirm:

-

## Scope

**In scope:** …
**Out of scope:** …

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| | | |

## Prerequisites

- [ ] Backups taken: <what, and where they are kept>
- [ ] Console or out-of-band access to <devices on the management path>
- [ ] Vault decrypted, collections built
- [ ] Preflight passes: `<command>`

## Procedure

### Step 1: <name>

What this step does, and whether it is disruptive.

**Run:**

```bash
<command>
```

**Verify:**

1. <observable result>

**Undo:** [Undo Step 1](#undo-step-1)

## Verification

The acceptance criteria for the change as a whole.

## Undo

Steps are backed out in reverse order. Name the point where undo stops being practical.

### Undo Step 1

<how to reverse step 1, or "No undo — <why>">

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ]
````

---

## Filling it in

- **Write Goal before Procedure.** If the end state cannot be stated as checkable facts, the
  change is not ready to plan.
- **Every step gets Run, Verify and Undo, and the undo is written before the change runs.**
  Where there is genuinely no undo, write that down; it marks the point of no return.
- **Take verification from the network, not from Ansible.** For the network roles,
  `--check --diff` is not a dry run and `changed=0` is not proof — see
  [Validation Checklist](/docs/runbook/change-management/#validation-checklist).
- **Record departures, don't edit them away.** When execution differs from the plan, leave the
  plan as it was and say what happened under **Outcome**. The plan and the outcome together
  are the record.
- **Link the incident** in the header table if the change caused one, and link the change from
  the [incident record](/docs/runbook/incident-management/incident-record-template/).
- **Retrospective records** — written for a change made before it had a record — say so in a
  note at the top, name their sources (plan, logs, git), and say "not recorded" where the
  sources are silent, rather than filling the gap.
