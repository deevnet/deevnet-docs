#!/usr/bin/env python3
"""Gather what a period's written account is drawn from. Run from the
repository root. Prints; changes nothing.

    period.py 2026-11      # a month
    period.py 2026-Q4      # a quarter
    period.py 2026         # a year
    period.py last         # the month before today, plus the quarter and year it closes

For the period it prints: the milestones reached, by area and item; the change
records and incidents dated in it; the open milestones of the items it touched;
incidents still open; and which accounts exist for it and for the periods below it.
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

def last_periods(today=None):
    today = today or datetime.date.today()
    first = today.replace(day=1)
    prev = first - datetime.timedelta(days=1)
    out = [f"{prev.year}-{prev.month:02d}"]
    if prev.month % 3 == 0: out.append(f"{prev.year}-Q{prev.month // 3}")
    if prev.month == 12: out.append(f"{prev.year}")
    return out

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

def records(lo, hi):
    rows = []
    for p in glob.glob("content/docs/changes/*/*.md") + glob.glob("content/docs/incidents/*/*.md"):
        if p.endswith("_index.md"): continue
        s = open(p, encoding="utf-8").read()
        d = re.search(r'\|\s*\*\*Date\*\*\s*\|\s*(\d{4}-\d{2}-\d{2})', s)
        st = re.search(r'\|\s*\*\*Status\*\*\s*\|([^\n]*)', s)
        rows.append((d.group(1) if d else "", title_of(p), re.sub(r'\{\{<[^>]*"([^"]+)"[^>]*>\}\}', r'\1', st.group(1)).strip(" |")[:90] if st else ""))
    return [r for r in rows if lo <= r[0] <= hi], [r for r in rows if r[1].startswith("INC") and not re.search(r'closed|resolved', r[2], re.I)]

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
    for k in (last_periods() if sys.argv[1] == "last" else [sys.argv[1]]):
        report(k)
