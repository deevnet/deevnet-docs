---
name: accomplishments
description: Track Deevnet's roadmap progress. Use to draft a month's, quarter's or year's account for the Roadmap Progress page (data/accomplishments/<period>.yaml), to catch the roadmap and every account up at any time, which is also what the monthly scheduled run does; and to backfill missing or misdated milestones from the git history of every Deevnet repository.
argument-hint: "[catch-up (the default)] | <period: 2026-11 | 2026-Q4 | 2026> | backfill <from> <to>"
---

# Roadmap Progress

The Roadmap Progress page (`content/docs/roadmap/progress.md`) lists every roadmap milestone
reached. Every month, quarter and year with a milestone shows a **written account**.
Each bullet opens onto the milestones behind it. Milestones reached since the last account fall
back to an automatic rollup until a catch-up writes it.

An account is `data/accomplishments/<period>.yaml`, where the period is `2026-10`, `2026-Q4`
or `2026`:

```yaml
# October 2026. Written from the month's milestones; each bullet names the roadmap items it rolls up.
through: "2026-10-31"  # the day it was written up to
reached: 59            # milestones done in the period when it was written
headline: "One sentence: what the period amounted to."
bullets:
  - text: "**A full-sentence bold lead-in.** Then what became true, with dates (Oct 5)."
    items: [infrastructure/substrate/tls-cert-automation, eds/eds/voice]   # under docs/roadmap/, or absolute
    within: "2026-Q1"     # a year's bullet about one quarter: whose milestones it opens onto
  - text: "A bullet with no items shows no milestones; use it for context, such as a quiet stretch."
next: "What comes next, from the open milestones."
watch: "Risks: open incidents, stalled records."
```

Every item named must exist; the build fails otherwise. `through` and `reached` are not shown on
the page. They are how a catch-up knows an account has fallen behind, so every account written or
revised sets them; `period.py <period>` prints the count.

## Catching up

Run at any time, with no arguments or by the monthly schedule. It brings everything up to today,
and running it again with nothing new does nothing.

1. **See what is due:** `python3 .claude/skills/accomplishments/scripts/period.py catchup` lists
   each period from the earliest month with an account up to today, lowest level first, as
   missing, stale or current. It also lists the records to check against the roadmap.
2. **Catch the roadmap up first,** with the `roadmap-update` skill. Where a listed record clearly
   reaches a milestone and gives its date, mark it done. List anything uncertain in the pull
   request instead; do not guess. Tenants such as EdS keep their records in their own
   repositories: check them if you can reach them, and otherwise say in the pull request that
   they were not checked. Then run `period.py catchup` again, since new milestones change what is
   due.
3. **Write what is due,** lowest level first, by [Drafting a period](#drafting-a-period):
   - **A missing account** is drafted. That includes a month, quarter or year still in progress,
     which says only what has happened so far. Its bullets may be fewer than the usual number.
   - **A stale account** is revised, not rewritten: keep every sentence still true, the owner's
     wording above all, and change or add only what the new milestones call for. A revised month
     makes its quarter and year stale, because they count the same milestones.
   - **A period with nothing reached** gets no account.
4. **Check and propose:** the `hugo-docs` check, then one pull request, `Accomplishments: catch-up
   to <today>`, on a branch `accomplishments-catch-up-<today>`. Its description has each account's
   headline and bullets, the milestones marked done, and anything left for the owner. **Do not
   merge it.** If nothing was due and the roadmap needed nothing, open no pull request and say so.

## Drafting a period

1. **Gather:** `python3 .claude/skills/accomplishments/scripts/period.py <period>` prints:
   - the milestones reached, by area and item;
   - the records dated in the period;
   - what is still open;
   - which accounts exist for the period and the periods below it.

   Read the records and plans behind anything unclear.
2. **Write from the level below.** This is what makes each level read differently:
   - **A month** is written from its milestones and records. It has a headline and 3–6 bullets
     (fewer in a thin month), each a theme rather than an item, with the days things landed. Then `next` and `watch`.
     It names things and dates them. It is for someone who follows the work.
   - **A quarter or year** may speak in the value objectives (`data/value_objectives.yaml`) where that says more than the items do. Existing accounts stay as written.
   - **A quarter** is written from its months' accounts. It has a headline and 3–5 outcomes, few
     dates, and a `watch` naming the one or two risks that matter. It says what changed and why it
     matters, not what was built. If a month has no account, draft that month first.
   - **A year** is written from its quarters. It has a headline, one bullet per quarter telling the
     arc, its lead-in opening `Q1:` (with `within` set), a bullet on what the platform now carries, and `next` as the outlook.
     It is for someone who wants the story in a minute.
   - **Never name the audience** (no "for a manager"). Write in that shape without saying so.
3. **Stay true to the record.** Claim nothing the milestones and records do not show. If the
   period's milestones are thin and the records show much more, say so to the owner; the fix is
   the roadmap (the `roadmap-update` skill, or a backfill), not a padded account. Write quiet
   stretches plainly: Deevnet is a part-time effort.
4. **Style:**
   - American English, short sentences, a full-sentence bold lead-in on each bullet;
   - CHG, INC and ADR IDs only where a reader would follow them;
   - no superlatives.
5. **Check:** the `hugo-docs` check. Then open a pull request with the account, and paste the
   headline and bullets into its description. A catch-up opens one pull request for all of them. **Do not merge it.**

## Backfilling milestones from history

When milestones are missing or dated only approximately, rebuild them from the git history of
every Deevnet repository, period by period. Read `references/history-dig.md` and follow it. It
fetches the history and splits it into periods, with one agent per period on a shared brief. It
merges their findings into one proposal for the owner, then applies it with the
`roadmap-update` skill.
