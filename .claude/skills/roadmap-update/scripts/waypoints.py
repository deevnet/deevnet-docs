#!/usr/bin/env python3
"""Read, check and mark the roadmap's waypoints (the `waypoints:` lists in
front matter). Run from the repository root.

    waypoints.py check
    waypoints.py list [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--status done|active|planned] [--page PATH]
    waypoints.py done PAGE TITLE DATE [--approx]
    waypoints.py status PAGE TITLE active|planned

PAGE is a path under content/docs/roadmap/ without .md (infrastructure/substrate/builder),
or a path from the repository root (content/projects/archive/x.md). TITLE is the exact
title, or a fragment that matches one waypoint only.

Pages read: roadmap items, archived plans and Completed Projects entries. Only the
list format this site writes is understood: one `- title:` per waypoint, then
`group:`, `value:`, `milestone:`, `status:`, `date:`, `approx:` on their own lines.

A waypoint with `milestone: true` closes a version: its definition of done, written in the
item's plan, is met. `list` marks it with 🏁.
"""
import argparse, glob, json, os, re, sys

STATUSES = ("done", "active", "planned")
ICON = {"done": "✅", "active": "🔄", "planned": "⏳"}

def is_plan(p):
    return p.endswith("/plan.md") or "/plan/" in p

def is_item(p):
    """A roadmap item: a plain page, or a section holding a plan or waypoints. Other sections are areas."""
    if is_plan(p): return False
    if not p.endswith("_index.md"): return True
    d = os.path.dirname(p)
    return os.path.exists(f"{d}/plan.md") or os.path.isdir(f"{d}/plan") or "\nwaypoints:" in open(p, encoding="utf-8").read()

def pages():
    out = [p for p in glob.glob("content/docs/roadmap/**/*.md", recursive=True) if is_item(p)]
    out += [p for p in glob.glob("content/projects/archive/*.md") + glob.glob("content/docs/completed/*.md") if not p.endswith("_index.md")]
    return sorted(out)

def resolve(page):
    if page.startswith("content/"): return page if page.endswith(".md") else page + ".md"
    p = f"content/docs/roadmap/{page.strip('/')}"
    return f"{p}/_index.md" if os.path.exists(f"{p}/_index.md") else f"{p}.md"

def split(path):
    s = open(path, encoding="utf-8").read()
    if not s.startswith("---\n"): return None
    end = s.index("\n---\n", 4)
    return s[:end], s[end:]

def parse(fm):
    if "\nwaypoints:" not in fm: return None
    head, rest = fm.split("\nwaypoints:", 1)
    lines = rest.split("\n")[1:]
    block, after = [], []
    for i, l in enumerate(lines):
        if l.startswith("  ") or not l.strip():
            block.append(l)
        else:
            after = lines[i:]; break
    ms = []
    for chunk in re.split(r'\n  - ', "\n" + "\n".join(block))[1:]:
        m = {}
        for k, v in re.findall(r'^\s*(title|group|value|milestone|status|date|approx): (.*)$', chunk, re.M):
            m[k] = json.loads(v) if v.startswith('"') else (v == "true" if k in ("approx", "milestone") else v)
        ms.append(m)
    return head, ms, after

def emit(head, ms, after):
    q = lambda s: json.dumps(s, ensure_ascii=False)
    y = ["waypoints:"]
    for m in ms:
        y.append(f"  - title: {q(m['title'])}")
        if m.get("group"): y.append(f"    group: {q(m['group'])}")
        if "value" in m: y.append(f"    value: {m['value']}")
        if m.get("milestone"): y.append("    milestone: true")
        y.append(f"    status: {m['status']}")
        if m["status"] == "done":
            y.append(f"    date: {q(m['date'])}")
            if m.get("approx"): y.append("    approx: true")
    return head + "\n" + "\n".join(y) + ("\n" + "\n".join(after) if after else "")

def find(ms, title):
    hit = [m for m in ms if m["title"] == title] or [m for m in ms if title.lower() in m["title"].lower()]
    if len(hit) != 1:
        sys.exit(f"{len(hit)} waypoints match {title!r}:\n  " + "\n  ".join(m["title"] for m in ms))
    return hit[0]

def cmd_check(_):
    errors = warnings = 0
    known = set(re.findall(r'^  - id: (\S+)$', open("data/value_objectives.yaml", encoding="utf-8").read(), re.M))
    def err(p, msg):
        nonlocal errors; errors += 1; print(f"ERROR {p}: {msg}")
    def warn(p, msg):
        nonlocal warnings; warnings += 1; print(f"warn  {p}: {msg}")
    for p in pages():
        parts = split(p)
        if not parts: continue
        fm, body = parts
        roadmap = p.startswith("content/docs/roadmap/")
        parsed = parse(fm)
        if not parsed:
            if roadmap and p not in ("content/docs/roadmap/progress.md", "content/docs/roadmap/value.md"): err(p, "no waypoints: list")
            continue
        head, ms, _ = parsed
        tags = re.findall(r'^value: \[(.*)\]$', head, re.M) + [m["value"].strip("[]") for m in ms if "value" in m]
        for v in {x.strip() for t in tags for x in t.split(",") if x.strip()} - known:
            err(p, f"value objective {v!r} is not in data/value_objectives.yaml")
        if roadmap and re.search(r'^tasks_(completed|in_progress|planned):', fm, re.M):
            err(p, "tasks_* on a roadmap page; its progress is computed from waypoints")
        seen = set()
        for m in ms:
            t = m.get("title", "?")
            if t in seen: err(p, f"duplicate title {t!r}")
            seen.add(t)
            if roadmap and len(re.sub(r'\([^)]*\)', '', t).split()) < 3:
                warn(p, f"{t!r}: too short to stand alone; say what became true")
            if m.get("status") not in STATUSES: err(p, f"{t!r}: status {m.get('status')!r}")
            if m.get("status") == "done":
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(m.get("date", ""))): err(p, f"{t!r}: done without a YYYY-MM-DD date")
            elif "date" in m: err(p, f"{t!r}: a date on a waypoint not done")
            if m.get("milestone") and roadmap and not os.path.exists(os.path.join(os.path.dirname(p), "plan.md")) and not os.path.isdir(os.path.join(os.path.dirname(p), "plan")):
                warn(p, f"{t!r}: a milestone with no plan to hold its definition of done")
        if roadmap:
            if "{{< waypoints" not in body: err(p, "the body has no {{< waypoints >}}")
            groups = set(re.findall(r'\{\{< waypoints group="([^"]+)" >\}\}', body))
            used = {m.get("group") for m in ms if m.get("group")}
            for g in used - groups: err(p, f"group {g!r} is never drawn")
            for g in groups - used: err(p, f"{{{{< waypoints group={g!r} >}}}} draws nothing")
            # An item holds 3–8 waypoints; one drawn under headings, 3–8 a heading.
            sizes = {}
            for m in ms: sizes[m.get("group")] = sizes.get(m.get("group"), 0) + 1
            for g, n in sizes.items():
                if n > 8: warn(p, f"{n} waypoints{' in ' + repr(g) if g else ''}; hold 3–8, split by theme")
    print(f"{errors} errors, {warnings} warnings")
    return 1 if errors else 0

def cmd_list(a):
    for p in pages():
        if a.page and p != resolve(a.page): continue
        parts = split(p); parsed = parts and parse(parts[0])
        if not parsed: continue
        title = re.search(r'^title: "?(.*?)"?$', parts[0], re.M).group(1)
        for m in parsed[1]:
            d = m.get("date", "")
            if a.status and m["status"] != a.status: continue
            if (a.date_from or a.date_to) and not d: continue
            if a.date_from and d < a.date_from: continue
            if a.date_to and d > a.date_to: continue
            rel = p[len("content/docs/roadmap/"):-3].removesuffix("/_index") if p.startswith("content/docs/roadmap/") else "/" + p[len("content/"):-3]
            print(f"{d or '-':10}\t{ICON[m['status']]}\t{rel}\t{title}\t{m['title']}" + ("\t(approx)" if m.get("approx") else "") + ("\t🏁" if m.get("milestone") else ""))
    return 0

def cmd_set(a, status, date=None, approx=False):
    p = resolve(a.page)
    fm, body = split(p)
    head, ms, after = parse(fm)
    m = find(ms, a.title)
    m["status"] = status
    m.pop("date", None); m.pop("approx", None)
    if status == "done":
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', date): sys.exit("DATE must be YYYY-MM-DD")
        m["date"] = date
        if approx: m["approx"] = True
    open(p, "w", encoding="utf-8").write(emit(head, ms, after) + body)
    print(f"{p}: {ICON[status]} {m['title']}" + (f" ({date})" if date else ""))
    return 0

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    l = sub.add_parser("list")
    l.add_argument("--from", dest="date_from"); l.add_argument("--to", dest="date_to")
    l.add_argument("--status", choices=STATUSES); l.add_argument("--page")
    d = sub.add_parser("done"); d.add_argument("page"); d.add_argument("title"); d.add_argument("date"); d.add_argument("--approx", action="store_true")
    s = sub.add_parser("status"); s.add_argument("page"); s.add_argument("title"); s.add_argument("new", choices=("active", "planned"))
    a = ap.parse_args()
    if a.cmd == "check": return cmd_check(a)
    if a.cmd == "list": return cmd_list(a)
    if a.cmd == "done": return cmd_set(a, "done", a.date, a.approx)
    return cmd_set(a, a.new)

if __name__ == "__main__":
    sys.exit(main())
