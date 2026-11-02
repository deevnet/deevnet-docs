---
name: roadmap-update
description: Keep the Deevnet roadmap and project plans true as work happens. Use when a change record or incident closes, when a plan's task or phase is done, when work starts on a roadmap item (write its plan), when a project graduates (archive its plan, add its Completed entry), when a roadmap item needs splitting, or when asked to check or recount the roadmap. Marks milestones done with their dates, keeps plans' task counts right, and keeps old URLs working.
argument-hint: "[what happened, e.g. 'CHG-0034 complete' or 'start Stratum 1']"
---

# Keep the roadmap and the plans true

The site's lifecycle is **Roadmap → Projects → Completed** (the CLAUDE.md "Document Domains"
list is the rule; read it first):

- A **roadmap item** (`content/docs/roadmap/**.md`) states intent and lists **3–8 milestones**
  in its front matter. Its progress is computed from them. It carries no `tasks_*`.
- A **project plan** (`<item>/plan.md`, beneath its item in the menu) holds the detail: phases,
  tasks as ✅ 🔄 ⏳ bullets, and hand-kept `tasks_*` counts. It is written once work starts.
- When a project is done, the plan moves to `content/projects/archive/`, a short entry goes in
  Completed Projects, and the roadmap item is removed.

Scripts (run from the repository root):

```bash
S=.claude/skills/roadmap-update/scripts
python3 $S/milestones.py check                       # every milestone list well formed
python3 $S/milestones.py list --status done --from 2026-11-01
python3 $S/milestones.py done   <page> "<title or unique fragment>" YYYY-MM-DD
python3 $S/milestones.py status <page> "<title>" active|planned
python3 $S/recount_plans.py [write]                  # plans' tasks_* from their bullets
```

`<page>` is the path under `content/docs/roadmap/` without `.md`, such as
`infrastructure/tenant-services/tenant-pki`.

## A milestone format

```yaml
milestones:
  - title: "The first Deevnet Pi (CHG-0056)"   # outcome-shaped; markdown allowed
    group: "Devices"      # only on pages drawn under headings, {{< milestones group="Devices" >}}
    value: [secure-by-default]   # optional: replaces the item's `value:` for this milestone
    status: done          # done | active | planned
    date: "2026-10-29"    # done only: the day it was reached
    approx: true          # rare: the date is only a latest possible one
```

A milestone is an **outcome someone would care about**, not a task: "Tenants' services on Deevnet
certificates", not "write the API endpoint". Name the record that carried it, in parentheses,
when there is one.

**A milestone serves value objectives.** Their ids are in `data/value_objectives.yaml`. Set `value:`
on the item when all its milestones serve the same ones, and on a milestone when it differs. Tag each
new milestone as it is added, because the bars on the Value Objectives page count them. Leave work
that serves none untagged rather than stretch a tag. `milestones.py check` fails on an unknown id.

**A milestone stands alone.** The Roadmap Progress page lists it away from its page and its
headings, so someone new to Deevnet must be able to tell what it means from its title alone. Name
the subject and say what became true: "Removing a tenant revokes its API token", not "Tokens";
"Automatic certificate renewal and expiry monitoring", not "Later". Do not reuse a plan's phase
heading as a title. Say what an in-house name is rather than using it: "the build server", not
"the Builder"; "EdS's voice service", not "voiced"; "the site's infrastructure", not "the
substrate". Products and industry terms (OpenBao, VLAN, MQTT) stay. `milestones.py check` warns on
titles under three words.

## When something is done

1. **Find what it completes.** A change record's `| **Date** |` row, its status, and the plan's
   phase it belongs to. Read the plan and the roadmap item.
2. **Update the plan:** mark the tasks ✅ (🔄 if partly), mark the phase heading, then
   `recount_plans.py write`. A finished phase stays open on the page; do not fold it.
3. **Update the roadmap item.**
   - If the work reaches a milestone, mark it done with `milestones.py done`. **The date is the
     day the last piece of work landed**: the record's date, or the commit's. It is not the day
     the docs were updated.
   - If a 🔄 milestone is too coarse to say done or not, split it: one done and dated milestone
     for what was reached, and one 🔄 or ⏳ for what remains.
   - If the work is an outcome no milestone covers, add one, placed in the order the item reads.
4. **Keep the item at 3–8 milestones.** Beyond 8, split the item by theme into new roadmap pages.
   Split its plan the same way: each item has its own plan and no plan serves two. Sibling plans
   link to each other. Keep the old plan's aliases on the first.
5. **Check:** `milestones.py check`, then the `hugo-docs` skill.

## When work starts on an item

Make the item a section: `git mv <item>.md <item>/_index.md`, add `bookCollapseSection: true`, and
write its plan at `<item>/plan.md`. The item stays the high-level summary; the plan is the detail,
and its short tasks fit on the one page. A very large effort may use `<item>/plan/_index.md` with
`requirements.md` and `tasks.md` beneath it. A plan holds:
- the front matter, with `title: "<Item>: Project Plan"`, `linkTitle: "Project Plan"`, weight and `tasks_*`;
- a `**Roadmap item:**` link back;
- `{{< overall-progress >}}` and the Legend;
- the phases with their tasks.

Move any detail on the roadmap page into the plan, and leave the roadmap page as its intro, the
progress bar, `{{< milestones >}}` and `**Project plan:** [Title](/docs/roadmap/<item>/plan/)`. Use
`git mv` when a page becomes a plan, so `git log --follow` keeps its history.

## When a project graduates

1. Every task is done or explicitly dropped.
2. `git mv` the plan to `content/projects/archive/<slug>.md`, with `title` back to the project's name and `linkTitle` dropped. Remove its roadmap link, and add the
   roadmap item's `milestones:` list and `area:` (the roadmap area it left) to its front matter, so
   Roadmap Progress keeps listing them.
3. Add a short entry in Completed Projects (`content/docs/completed/`) linking to the archived
   plan, or to the project's own site.
4. Remove the roadmap item. Put its URLs in the archived plan's `aliases:`.

## Rules

- **Old URLs keep working.** A page that moves keeps its old paths in `aliases:`. The `hugo-docs`
  check fails on a lost URL.
- **Accepted records are not rewritten** to repoint links; their old links resolve through aliases.
- **Write American English**, and follow CLAUDE.md's documentation guidelines: lead with what is,
  short headings, and full-sentence bold lead-ins.
- **Do not invent dates.** If the evidence does not give a day, say so and ask.
- Work in a worktree on a branch, and open a pull request. **Do not merge it**; the owner does.
