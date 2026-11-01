---
name: accomplishments
description: Write up what Deevnet accomplished. Use to draft a month's, quarter's or year's account for the Accomplishments page (data/accomplishments/<period>.yaml), including the scheduled monthly run ("last" drafts the month just ended, and the quarter and year it closes); and to backfill missing or misdated milestones from the git history of every Deevnet repository.
argument-hint: "<period: 2026-11 | 2026-Q4 | 2026 | last> | backfill <from> <to>"
---

# Accomplishments

The Accomplishments page (`content/docs/roadmap/accomplishments.md`) lists every roadmap
milestone reached. In Summary, a period with a **written account** shows it. Each bullet opens
onto the milestones behind it. Periods without an account fall back to an automatic rollup.

An account is `data/accomplishments/<period>.yaml`, where the period is `2026-10`, `2026-Q4`
or `2026`:

```yaml
# October 2026. Written from the month's milestones; each bullet names the roadmap items it rolls up.
headline: "One sentence: what the period amounted to."
bullets:
  - text: "**A full-sentence bold lead-in.** Then what became true, with dates (Oct 5)."
    items: [infrastructure/substrate/tls-cert-automation, eds/eds/voice]   # under docs/roadmap/, or absolute
    within: "2026-Q1"     # a year's bullet about one quarter: whose milestones it opens onto
  - text: "A bullet with no items shows no milestones; use it for context, such as a quiet stretch."
next: "What comes next, from the open milestones."
watch: "Risks: open incidents, stalled records."
```

Every item named must exist; the build fails otherwise.

## Drafting a period

1. **Gather:** `python3 .claude/skills/accomplishments/scripts/period.py <period>` prints:
   - the milestones reached, by area and item;
   - the records dated in the period;
   - what is still open;
   - which accounts exist for the period and the periods below it.

   Read the records and plans behind anything unclear.
2. **Write from the level below.** This is what makes each level read differently:
   - **A month** is written from its milestones and records. It has a headline and 3–6 bullets,
     each a theme rather than an item, with the days things landed. Then `next` and `watch`.
     It names things and dates them. It is for someone who follows the work.
   - **A quarter** is written from its months' accounts. It has a headline and 3–5 outcomes, few
     dates, and a `watch` naming the one or two risks that matter. It says what changed and why it
     matters, not what was built. If a month has no account, draft that month first.
   - **A year** is written from its quarters. It has a headline, one bullet per quarter telling the
     arc (with `within` set), a bullet on what the platform now carries, and `next` as the outlook.
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
   headline and bullets into its description. **Do not merge it.**

## Scheduled run (`last`)

Run on the 1st of each month: `period.py last` names the month just ended, plus the quarter and
year it closes. Then:
1. Draft each missing account, lowest level first: the month, then the quarter, then the year.
   Never overwrite an account that exists. If one already exists, note it and skip it.
2. If the month reached no milestones, write no account; say so in the pull request instead.
3. Before drafting, check that the month's work reached the roadmap. Look for change records
   completed in the month whose milestone is not marked done, and list them in the pull request
   as roadmap updates the owner may want. Do not apply them unasked.
4. Open one pull request, `Accomplishments: <period(s)>`, on a branch `accomplishments-<month>`.

## Backfilling milestones from history

When milestones are missing or dated only approximately, rebuild them from the git history of
every Deevnet repository, period by period. Read `references/history-dig.md` and follow it. It
fetches the history and splits it into periods, with one agent per period on a shared brief. It
merges their findings into one proposal for the owner, then applies it with the
`roadmap-update` skill.
