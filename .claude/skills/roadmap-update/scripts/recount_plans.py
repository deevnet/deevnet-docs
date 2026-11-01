#!/usr/bin/env python3
"""Recount the project plans' task counts (tasks_completed, tasks_in_progress,
tasks_planned) from their ✅ 🔄 ⏳ bullets; a phase heading marked ✅ 🔄 ⏳
with no task bullets beneath it counts as one task. Run from the repository root.

    recount_plans.py          # show plans whose counts are wrong
    recount_plans.py write    # and fix them

Plans are a roadmap item's plan.md (or the pages of its plan/ section) and
content/projects/archive/*.md. Roadmap items have no counts: their progress is
computed from their milestones.
"""
import glob, re, sys

KEYS = ("tasks_completed", "tasks_in_progress", "tasks_planned")
BULLET = re.compile(r'^\s*- (✅|🔄|⏳)', re.M)
FM = re.compile(r'^---\n(.*?)\n---\n', re.S)

def main():
    write = len(sys.argv) > 1 and sys.argv[1] == "write"
    wrong = 0
    plans = glob.glob("content/docs/roadmap/**/plan.md", recursive=True) + glob.glob("content/docs/roadmap/**/plan/*.md", recursive=True)
    for p in sorted(plans + glob.glob("content/projects/archive/*.md")):
        if p.endswith("_index.md"): continue
        s = open(p, encoding="utf-8").read()
        m = FM.match(s)
        if not m: continue
        fm, body = m.group(1), s[m.end():]
        b = []
        for sec in re.split(r'^(?=#{2,3} )', body, flags=re.M):
            found = BULLET.findall(sec)
            head = re.match(r'#{2,3} .*?(✅|🔄|⏳)\s*$', sec.split("\n", 1)[0])
            b += found if found or not head else [head.group(1)]
        new = (b.count("✅"), b.count("🔄"), b.count("⏳"))
        old = tuple(int(x.group(1)) if (x := re.search(rf'^{k}: (\d+)', fm, re.M)) else None for k in KEYS)
        if new == old: continue
        wrong += 1
        print(f"{p:50} {old} -> {new}")
        if write:
            for k, v in zip(KEYS, new):
                fm = re.sub(rf'^{k}: .*$', f"{k}: {v}", fm, flags=re.M) if re.search(rf'^{k}:', fm, re.M) else fm + f"\n{k}: {v}"
            open(p, "w", encoding="utf-8").write(f"---\n{fm}\n---\n" + body)
    print(f"{wrong} plans {'fixed' if write else 'with wrong counts'}")
    return 1 if wrong and not write else 0

if __name__ == "__main__":
    sys.exit(main())
