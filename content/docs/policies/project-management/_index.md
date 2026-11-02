---
title: "Project Management"
weight: 5
bookCollapseSection: true
---

# Project Management

How a project goes from an idea to done: a proposal first, a plan once the proposal is accepted,
progress shown on the roadmap as work lands, and the project graduated when it is finished. The
owner decides at each step; the skills named below draft, and the owner accepts or changes what
they draft.

---

## Principles

- **An idea is shaped before it is planned.** What it is for, what it is not, and the smallest
  version worth having are written down before any plan or roadmap item exists.
- **Building can start before the plan.** A working prototype is welcome while a proposal is being
  written, and is often how its requirements are found. It is not a commitment to the design.
- **Nothing is decided from a draft.** While a proposal is in draft, it opens no ADRs: its
  questions stay open in the proposal and the requirements until it is accepted.
- **A version is done when its definition of done is met.** The definition is written before the
  version's work starts and then fixed. A new idea goes to the next version, never into the
  current one; changing the current one is the owner's deliberate call, noted with its date.
- **Progress is counted from waypoints**, never from hand-kept percentages, and a waypoint is
  marked done, with its date, in the same commit as the work that reaches it.

---

## The steps

| Step | What is written | Where | With |
|---|---|---|---|
| **1. Proposal** | What the idea is for, what it is and is not, the MVP, a rough version cut, open questions | The project's own docs if it has a repository (`architecture/proposals/`), otherwise [Architecture](/docs/architecture/) here | `/cd:ideation` |
| **2. Requirements** | What it must do, settled and open, and the cases it must get right | Beside the proposal | Conversation with the owner |
| **3. Plan** | Versions, each with a definition of done (v1 the MVP); the roadmap item with its waypoints, and its project plan beneath it | [Roadmap](/docs/roadmap/), `roadmap/<area>/<item>` and its `plan.md` | `/cd:version-planning` |
| **4. Building** | Waypoints marked done with their dates; a milestone when a version's definition of done is met; ADRs, change and incident records as the work calls for them | The roadmap item; the records' own sections | `roadmap-update` |
| **5. Progress** | A written account of each month, quarter and year | [Roadmap Progress](/docs/roadmap/progress/), `data/accomplishments/` | `/cd:progress-reporting` |
| **6. Done** | The project graduates: its plan is archived and an entry written | [Completed Projects](/docs/completed/) | `roadmap-update` |

### 1. Proposal

A proposal is one page, in the voice of the repository it lives in. Its status moves from
**Draft** (being written and reviewed) to **Proposal** (finished, waiting on the owner's decision)
to **Accepted**, when the owner accepts it and planning starts, or **Declined**. A proposal is not
part of the decision log; it links to the ADRs written once it is accepted.

A project with a repository of its own keeps its proposal there, beside its code
([eds-inventory's MVP](https://cdeever.github.io/eds-inventory/docs/architecture/proposals/mvp/)
is one). A project with no repository yet is proposed here.

### 2. Requirements

The requirements say what the project must do, plainly, with what is still open listed as
questions rather than guessed. Cases it must get right are kept by name, so each becomes a test.
A question settled while the proposal is in draft is written into the requirements; it becomes an
ADR, if it needs one, once the proposal is accepted.

### 3. Plan

Once the proposal is accepted, `/cd:version-planning` cuts its versions with the owner and writes
them into Deevnet's roadmap: a roadmap item with 3–8 waypoints, the last of each version marked
`milestone: true`, and a project plan beneath it with the versions, their definitions of done,
phases and tasks. Only the current version needs a full definition of done; later versions have a
goal and a sketch until they become current.

### 4. Building

Work is carried out by the usual procedures: [Change Management](../change-management/) for what
it changes on a site, [Incident Management](../incident-management/) for what breaks, and ADRs for
the design forks. A waypoint is marked done when the work that reaches it is committed. When a
version's definition of done is met, its milestone is marked done and the next version's
definition of done is written.

### 5. Progress

[Roadmap Progress](/docs/roadmap/progress/) is drawn from the waypoints at every build. A day or a
week lists the waypoints reached in it. A month, quarter or year shows its written account, drafted
by `/cd:progress-reporting` and reviewed by the owner as a pull request; waypoints reached after an
account was written are listed beneath it until it is written again. The period today falls in is
marked in progress, with the days left in it.

Two **catch-ups** keep it current, both on a schedule and both able to run by hand:

| | Light | Heavy |
|---|---|---|
| **When** | Daily | The 1st of each month |
| **What** | Checks the records against the waypoints, and marks done what a record clearly reaches, with its day | The light run's work, then drafts each account that is missing and revises each that has fallen behind, month, quarter and year |
| **Keeps current** | The day and week views, and the waypoints beneath each account | The written accounts |
| **Uncertain waypoints** | Left alone | Listed for the owner |
| **Pull request** | Merged by itself once its checks pass | Reviewed and merged by the owner |
| **Cost** | Small: a read of the day's records | Larger: every stale account rewritten, and a revised month makes its quarter and year stale |

Either run that finds nothing new changes nothing and opens no pull request. Both are
`/cd:progress-reporting`: `light`, or a plain catch-up for the heavy one.

### 6. Done

When every version planned is done, the project graduates: its plan moves to the
[archive](/projects/archive/) with its waypoints, so Roadmap Progress keeps them; its roadmap item
is removed; and an entry is added to [Completed Projects](/docs/completed/).
