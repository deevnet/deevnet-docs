---
title: "Certification Record Template"
weight: 3
---

# Certification Record Template

The shape of a certification: one **item page** per model or product, and one **revision page**
per evaluation beneath it. Copy the skeletons below.

---

## Where it goes

| | Hardware | Software |
|---|---|---|
| **Item** | `content/docs/platforms/certification/hardware/<layer>/<model>/_index.md` | `content/docs/platforms/certification/software/<layer>/<product>/_index.md` |
| **Revision** | `…/<model>/<YYYY-MM>-hw-<revision>.md`, e.g. `2026-10-hw-1-20.md` | `…/<product>/<line>.md`, e.g. `26-7.md` |
| **Layer** | `network`, `management-plane` or `tenant-compute`, as on [Implementation & Tooling](/docs/platforms/) | the same, or `tooling` for build and automation tools |
| **Item title** | The model, e.g. "TP-Link SG2218" | The product, e.g. "OPNsense" |
| **Revision title** | "2026-10 · hardware 1.20" | "26.7" |
| **Weight** | The first revision is `1000`, and each new one is one lower, so the newest sorts first | the same |
| **Index** | Add the item to its layer page, and to [Certification](/docs/platforms/certification/) | the same |

Add `bookCollapseSection: true` to every item page, so its revisions stay folded in the sidebar.

---

## Item page skeleton

````markdown
---
title: "<Model or product>"
bookCollapseSection: true
---

# <Model or product>

| | |
|---|---|
| **Role** | <what it is certified for, e.g. core router> |
| **Current** | {{</* status-badge "complete" "Certified" */>}} <revision or line> |
| **Selected on** | [<platform page>](/docs/platforms/...) |
| **In the catalog** | [Software Catalog](/docs/platforms/software-catalog/#...) *(software only)* |

<One paragraph: what it is and why it was evaluated.>

## Revisions

| Revision | Date | Verdict | Notes |
|---|---|---|---|
| [<revision>](<slug>/) | YYYY-MM-DD | Certified | <one line> |
````

---

## Revision page skeleton

````markdown
---
title: "<revision>"
weight: <1000 for the first revision; one lower for each after>
---

# <Model or product>: <revision>

| | |
|---|---|
| **Verdict** | {{</* status-badge "evaluating" "Under evaluation" */>}} |
| **Date** | YYYY-MM-DD (evaluation started) · YYYY-MM-DD (verdict) |
| **Role** | <role> |
| **Tested with** | <hardware: the OS and driver · software: the hardware and the bundled components the role uses> |
| **Environment** | <bench / throwaway / on site, and what that means for the evidence> |
| **Supersedes** | <previous revision, or None> |

## Criteria

| Area | Tested | How | Result |
|---|---|---|---|
| <area from the process page> | yes / no / not tested | <what was done> | <what was seen> |

## Conditions

<Certified with conditions only: each condition, and what would clear it. Otherwise "None".>

## Findings

<Anything learned that isn't a criterion result, and where it went: a risk, an incident, a follow-up.>

## Addenda

<Dated, appended only: patch releases re-checked against a criterion, and why.>
````
