#!/usr/bin/env python3
"""Build the docs site and check it: Hugo's own result, warnings new against
a base (origin/main by default), every internal link and anchor, and every
page moved or removed since the base still answering at its old URL.

    python3 .claude/skills/hugo-docs/scripts/check.py [--base REF | --no-base]

Run from anywhere inside the repository or one of its worktrees. Exits 1 if
anything fails. Changes nothing in the repository; builds go to a temp dir.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile

def run(cmd, cwd, check=True):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"failed: {' '.join(cmd)}\n{r.stderr}")
    return r

def build(root, out):
    # The theme is a submodule; a fresh worktree has it empty, and Hugo then
    # builds nothing useful. Initialize it, borrowing objects from the main clone.
    main = run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"], root).stdout.strip()
    ref = os.path.join(os.path.dirname(main), "themes", "hugo-book")
    args = ["git", "submodule", "update", "--init", "-q"]
    if os.path.isdir(os.path.join(ref, ".git")) or os.path.isfile(os.path.join(ref, ".git")):
        args += ["--reference", ref]
    run(args, root)
    r = run(["hugo", "-d", out], root, check=False)  # Hugo's own exit code, not a pipe's
    warns = [re.sub(r'\s+', ' ', l).strip() for l in (r.stdout + r.stderr).splitlines() if l.startswith(("WARN", "ERROR"))]
    return r.returncode, warns, r.stdout + r.stderr

def url_of(path):
    """content/docs/a/b.md -> docs/a/b ; content/docs/a/_index.md -> docs/a"""
    p = path[len("content/"):-len(".md")]
    return p[:-len("/_index")] if p.endswith("/_index") else p

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--no-base", action="store_true")
    a = ap.parse_args()
    root = run(["git", "rev-parse", "--show-toplevel"], os.getcwd()).stdout.strip()
    tmp = tempfile.mkdtemp(prefix="hugo-check-")
    failed = False
    try:
        out = os.path.join(tmp, "site")
        rc, warns, log = build(root, out)
        pages = sum(1 for _, _, fs in os.walk(out) for f in fs if f == "index.html") if rc == 0 else 0
        print(f"build: {'ok' if rc == 0 else 'FAILED (exit %d)' % rc}, {pages} pages, {len(warns)} warnings")
        if rc:
            print(log[-3000:]); return 1

        if not a.no_base:
            bdir = os.path.join(tmp, "base")
            run(["git", "worktree", "add", "-q", "--detach", bdir, a.base], root)
            try:
                brc, bwarns, _ = build(bdir, os.path.join(tmp, "base-site"))
            finally:
                run(["git", "worktree", "remove", "--force", bdir], root, check=False)
            new = [w for w in warns if w not in set(bwarns)]
            print(f"warnings new against {a.base}: {len(new)}")
            for w in new: print("  " + w[:200])
            failed |= bool(new)

            # Pages removed or renamed since the base must still answer at their old URL.
            diff = run(["git", "diff", "--name-status", "-M", a.base, "--", "content"], root).stdout
            lost = []
            for line in diff.splitlines():
                f = line.split("\t")
                if f[0][0] in "DR" and f[1].endswith(".md"):
                    old = url_of(f[1])
                    if not os.path.exists(os.path.join(out, old, "index.html")):
                        lost.append(old)
            print(f"old URLs lost: {len(lost)}")
            for u in lost: print(f"  /{u}/  (add it to the moved page's aliases)")
            failed |= bool(lost)
        else:
            print("warnings:", *warns, sep="\n  ") if warns else None

        bad = n = 0
        link = re.compile(r'\]\((/(?:docs|projects)/[^)\s#]*)(#[^)\s]*)?\)')
        # Pages, and the data files whose markdown pages draw (the Software Catalog's rows).
        for dp, _, fs in [*os.walk(os.path.join(root, "content")), *os.walk(os.path.join(root, "data"))]:
            for f in fs:
                if not f.endswith((".md", ".yaml")): continue
                p = os.path.join(dp, f)
                for target, anchor in link.findall(open(p, encoding="utf-8").read()):
                    if "..." in target + anchor: continue  # a template's placeholder
                    n += 1
                    t = target.strip("/")
                    page = os.path.join(out, t) if os.path.splitext(t)[1] else os.path.join(out, t, "index.html")
                    rel = os.path.relpath(p, root)
                    if not os.path.exists(page):
                        print(f"  broken link: {rel} -> {target}"); bad += 1
                    elif anchor and not re.search(r'id="?%s[" >]' % re.escape(anchor[1:]), open(page, encoding="utf-8").read()):
                        print(f"  broken anchor: {rel} -> {target}{anchor}"); bad += 1
        print(f"internal links: {n} checked, {bad} broken")
        failed |= bool(bad)
        return 1 if failed else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
