---
name: hugo-docs
description: Build and check the Deevnet docs site. Use after editing anything in content/, layouts/, data/ or assets/, and before committing or opening a pull request. Builds with Hugo (initializing the theme submodule first), compares warnings with origin/main, checks every internal link and anchor, and checks that moved or removed pages still answer at their old URLs.
argument-hint: "[--base REF | --no-base]"
---

# Check the docs site

Run the check from the repository or any of its worktrees:

```bash
python3 .claude/skills/hugo-docs/scripts/check.py            # against origin/main
python3 .claude/skills/hugo-docs/scripts/check.py --no-base  # build and links only
```

It builds into a temporary directory and changes nothing in the repository. It reports:

- **The build**, from Hugo's own exit code and the page count. Never judge a build by a pipe's
  exit code (`hugo | tail` is always 0), and never by a quiet output alone.
- **Warnings new against the base.** The site already has a few deprecation warnings from newer
  Hugo releases; only warnings the change adds count.
- **Old URLs lost.** Every page removed or renamed since the base must still build at its old
  URL, through `aliases:` in the moved page's front matter.
- **Internal links and anchors** (`](/docs/…)`, `](/projects/…)`) that do not resolve, in pages and
  in the data files pages draw from (`data/*.yaml`).

It exits 1 if any of these fail. Report the result plainly: what passed, what failed, with the
file and link for each failure.

## Things to know

- **The theme is a git submodule** (`themes/hugo-book`). A fresh worktree has it empty, and Hugo
  then builds a site with no layouts. The script initializes it; if building by hand, run
  `git submodule update --init` first.
- **CI builds with Hugo 0.140.1** (`.github/workflows/hugo.yml`), older than a local install may
  be. Templates must work there: use `site.Data`, not `hugo.Data`, even though newer Hugo warns.
- **The site deploys from `main`** through GitHub Pages; after a merge,
  `gh run list --workflow hugo.yml --limit 1` shows whether it published.

## Do not

- Do not start `hugo server` unless asked; to look at a page, build it and read the HTML, or use
  a browser on a server you stop afterward.
- Do not deploy, publish or merge.
