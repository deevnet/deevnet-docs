#!/usr/bin/env python3
"""Gather what a period's written account is drawn from. Run from the
repository root. Prints; changes nothing.

    period.py 2026-11      # a month
    period.py 2026-Q4      # a quarter
    period.py 2026         # a year
    period.py catchup      # what a catch-up has to do today

For a period it prints: the milestones reached, by area and item; the change
records and incidents dated in it; the open milestones of the items it touched;
incidents still open; and which accounts exist for it and for the periods below it.

Catchup prints each period from the earliest month with an account up to today,
lowest level first, and whether its account is missing, stale or current. An
account is stale when its `reached:` count differs from the milestones now done
in the period, which also catches milestones backfilled into an earlier date. It
then prints the records to check against the roadmap.
"""
import calendar, datetime, glob, os, re, subprocess, sys

ROADMAP = "content/docs/roadmap/"

def bounds(key):
    if re.fullmatch(r'\d{4}', key):
        return f"{key}-01-01", f"{key}-12-31", "year"
    m = re.fullmatch(r'(\d{4})-Q([1-4])', key)
    if m:
        y, q = int(m.group(1)), int(m.group(2))
        last = calendar.monthrange(y, q * 3)[1]
        return f"{y}-{q*3-2:02d}-01", f"{y}-{q*3:02d}-{last}", "quarter"
    m = re.fullmatch(r'(\d{4})-(\d{2})', key)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        return f"{key}-01", f"{key}-{calendar.monthrange(y, mo)[1]}", "month"
    sys.exit(f"not a period: {key} (YYYY-MM, YYYY-Qn or YYYY)")

def below(key, kind):
    y = key[:4]
    if kind == "year": return [f"{y}-Q{q}" for q in range(1, 5)]
    if kind == "quarter":
        q = int(key[-1]); return [f"{y}-{m:02d}" for m in range(q * 3 - 2, q * 3 + 1)]
    return []

def title_of(path):
    s = open(path, encoding="utf-8").read()
    m = re.search(r'^title: "?(.*?)"?$', s, re.M)
    return re.sub(r'^\W+\s*', '', m.group(1)) if m else path

def area_of(rel):
    if rel.startswith("/"): return "Graduated projects"
    top = rel.split("/")[0]
    idx = f"{ROADMAP}{top}/_index.md"
    return title_of(idx) if os.path.exists(idx) else title_of(f"{ROADMAP}{top}.md")

def milestones(args):
    ms = os.path.join(os.path.dirname(__file__), "..", "..", "roadmap-update", "scripts", "milestones.py")
    out = subprocess.run([sys.executable, ms, "list"] + args, capture_output=True, text=True, check=True).stdout
    return [l.split("\t") for l in out.splitlines() if l.strip()]

def all_records():
    rows = []
    for p in glob.glob("content/docs/changes/*/*.md") + glob.glob("content/docs/incidents/*/*.md"):
        if p.endswith("_index.md"): continue
        s = open(p, encoding="utf-8").read()
        d = re.search(r'\|\s*\*\*Date\*\*\s*\|\s*(\d{4}-\d{2}-\d{2})', s)
        st = re.search(r'\|\s*\*\*Status\*\*\s*\|([^\n]*)', s)
        rows.append((d.group(1) if d else "", title_of(p), re.sub(r'\{\{<[^>]*"([^"]+)"[^>]*>\}\}', r'\1', st.group(1)).strip(" |")[:90] if st else ""))
    return rows

def records(lo, hi):
    rows = all_records()
    return [r for r in rows if lo <= r[0] <= hi], [r for r in rows if r[1].startswith("INC") and not re.search(r'closed|resolved', r[2], re.I)]

def account_field(key, field):
    f = f"data/accomplishments/{key}.yaml"
    if not os.path.exists(f): return None
    m = re.search(rf'^{field}:\s*"?([^"\n]+?)"?\s*$', open(f, encoding="utf-8").read(), re.M)
    return m.group(1) if m else None

def catchup_periods(today):
    this = f"{today.year}-{today.month:02d}"
    written = [os.path.basename(f)[:-5] for f in glob.glob("data/accomplishments/*.yaml")]
    y, mo = map(int, min([k for k in written if re.fullmatch(r'\d{4}-\d{2}', k)] + [this]).split("-"))
    months, quarters, years = [], [], []
    while f"{y}-{mo:02d}" <= this:
        months.append(f"{y}-{mo:02d}")
        for out, k in ((quarters, f"{y}-Q{(mo + 2) // 3}"), (years, f"{y}")):
            if k not in out: out.append(k)
        y, mo = (y + 1, 1) if mo == 12 else (y, mo + 1)
    return months + quarters + years

def catchup(today=None):
    today = today or datetime.date.today()
    print(f"# Catch-up as of {today}\n\n## Accounts\n")
    due, throughs = 0, []
    for key in catchup_periods(today):
        lo, hi, _ = bounds(key)
        n = len(milestones(["--from", lo, "--to", hi, "--status", "done"]))
        exists = os.path.exists(f"data/accomplishments/{key}.yaml")
        reached, through = account_field(key, "reached"), account_field(key, "through")
        if through: throughs.append(through)
        if not exists: state = "missing" if n else "nothing reached"
        elif reached != str(n): state = f"stale (written with {reached or 'no count'})"
        else: state = "current"
        due += state.startswith(("missing", "stale"))
        partial = "  in progress" if hi >= today.isoformat() else ""
        print(f"- {key}: {n} reached, {state}{partial}")
    print(f"\nAccounts to write or revise: {due}")
    since = max(throughs) if throughs else today.replace(day=1).isoformat()
    print(f"\n## Records to check against the roadmap (dated from {since}, or in progress)\n")
    for d, t, st in sorted(all_records()):
        if d >= since or re.search(r'in progress', st, re.I):
            print(f"- {d or '?':10}  {t}  — {st}")
    print()

def report(key):
    lo, hi, kind = bounds(key)
    print(f"# {key} ({kind}, {lo} to {hi})\n")
    reached = milestones(["--from", lo, "--to", hi, "--status", "done"])
    print(f"## Milestones reached: {len(reached)}\n")
    by = {}
    for d, _, rel, item, title, *rest in reached:
        by.setdefault(area_of(rel), {}).setdefault((rel, item), []).append((d, title, bool(rest)))
    for area, items in by.items():
        print(f"### {area}")
        for (rel, item), rows in sorted(items.items(), key=lambda x: -len(x[1])):
            print(f"- {item}  [items: {rel}]")
            for d, t, approx in sorted(rows):
                print(f"  - {'by ' if approx else ''}{d}  {t}")
        print()
    touched = {rel for _, _, rel, *_ in reached}
    print("## Still open in the items touched (for Next)\n")
    for rel in sorted(touched):
        rows = [r for r in milestones(["--page", rel]) if r[1] != "✅"]
        if rows:
            print(f"- {rows[0][3]}: " + "; ".join(f"{r[1]} {r[4]}" for r in rows))
    dated, open_inc = records(lo, hi)
    print(f"\n## Records dated in the period: {len(dated)}\n")
    for d, t, st in sorted(dated):
        print(f"- {d}  {t}  — {st}")
    print("\n## Incidents not closed (for Watch)\n")
    for d, t, st in sorted(open_inc):
        print(f"- {d or '?':10}  {t}  — {st}")
    print("\n## Written accounts\n")
    for k in [key] + below(key, kind):
        f = f"data/accomplishments/{k}.yaml"
        print(f"- {k}: {'written' if os.path.exists(f) else 'none'}  ({f})")
    print()

if __name__ == "__main__":
    if len(sys.argv) != 2: sys.exit(__doc__)
    if sys.argv[1] == "catchup": catchup()
    else: report(sys.argv[1])
