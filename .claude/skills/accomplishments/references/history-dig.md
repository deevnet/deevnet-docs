# Backfill from history

How the roadmap's history was rebuilt in November 2026. Use it when waypoints are missing,
coarse, or dated only approximately, or when a stretch of work was never put on the roadmap.

## 1. Fetch every repository's history

The roadmap covers more than this repository. Fetch history only, into a scratch directory,
with git's credential helper off: the repositories are public, and macOS otherwise prompts for
the Keychain.

```bash
D=<scratch>/history; mkdir -p "$D"; cd "$D"
for r in $(gh repo list deevnet --limit 100 --json name -q '.[].name'); do
  GIT_TERMINAL_PROMPT=0 git -c credential.helper= clone -q --bare --filter=blob:none \
    "https://github.com/deevnet/$r" "$r.git"
  git -C "$r.git" config credential.helper ""
done
# Tenants' own repositories too, when their items are in question (MaBell: cdeever/esp32-ma-bell-gateway).
```

## 2. Find the shape

Count commits per repository per month across all of them:
`git -C X.git log --all --no-merges --format=%ad --date=format:%Y-%m`. The pattern of busy and
quiet stretches decides how to split the work. Quiet stretches are not failures. Deevnet is a
part-time effort, and a narrative says so plainly.

## 3. One agent per period, in parallel

Split the history into 3–4 periods of about equal weight, cutting at quiet stretches, and give
each period to a general-purpose agent. Give each agent the same brief, changing only the
period and any hints about what is known to fall in it:

> Reconstruct what the Deevnet project accomplished from **<from> to <to>**, from its git
> history, so its roadmap can show dated waypoints. Read only.
>
> Sources: bare clones at `<scratch>/history/*.git` (`git -C X.git log --all --no-merges
> --since=… --until=… --format='%ad %h %s%n%b' --date=short`; `--merges` gives PR titles); the
> docs at `<repo>`: change records `content/docs/changes/`, incidents, ADRs, the roadmap's
> `waypoints:` front matter, and each item's plan (`plan.md`) beneath it.
>
> Report, under ~2000 words:
> 1. What happened, week by week: things that became true, each with a date and evidence
>    (record ID or repo + short sha). Skip churn. Explain gaps.
> 2. Mapping onto the roadmap: waypoints the evidence shows reached, with the date the last
>    piece landed (flag disagreements with dates already there); 🔄/⏳ waypoints partly or
>    fully done, with a proposed split into dated pieces plus what remains; missing waypoints,
>    each with an outcome-shaped title, its item, a date and evidence. Waypoint-sized only.
> 3. The period in 3–5 lines.
>
> Be conservative: every date from evidence; say when it is a guess.

## 4. Merge, then ask

Merge the reports into one proposal, grouped as date corrections, splits, new waypoints, and
things left out on purpose. Fold duplicates: the same outcome is often found by two agents, or
proposed under two items. Then put it to the owner before writing anything. Ask about facts that
only the owner knows, such as why a stretch was quiet or what failed.

## 5. Apply

Apply the agreed changes with the `roadmap-update` skill's `waypoints.py`, or by editing the
front matter directly for splits and inserts. Keep every reached waypoint dated. Remove `approx`
wherever the evidence now gives the day. Then run `waypoints.py check` and the `hugo-docs`
check, and open a pull request.
