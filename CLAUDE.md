# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This is the **authoritative documentation repository** for the Deevnet ecosystem. It contains no code—only documentation that defines standards, architecture, and policies that apply across all Deevnet repositories.

## This Instance

This site documents the **Mobile Factory**, the mobile instance of Deevnet (site code `02`, zone `mobile.deevnet.net`), published as **Deevnet IoTaaS** (Deevnet IoT as a Service); its long form is the Deevnet IoTaaS Mobile Development Factory. **The Mobile Factory builds sites and tenants.** Its sites are itself and the home site (site code `01`, zone `home.deevnet.net`); its tenants are the devices and services it creates, wherever they are deployed. Everything is built at the factory and deployed from the Builder. Architecture, Standards and Policies & Procedures are written for any Deevnet site; Implementation & Tooling, the Runbook, the change and incident records, and the Roadmap are the factory's, including what it deploys at other sites (a record names its site in the Site column). **The home site is not built yet** ([Home Site](content/docs/roadmap/infrastructure/home-site.md) roadmap item): document it only as it is built, never ahead of the code. Its old documentation, archived at the git tag `archive/home-site-2026-09`, is history, not a source.

## Key Principles

- **Standards are authoritative**: If a project conflicts with standards defined here, standards win
- **Documentation is normative**: Documents define expectations and contracts, not just descriptions
- **Intent over implementation**: This repo defines "what" and "why"; implementation details live in their respective repositories
- **Explicit versioning**: Standards are versioned; repositories should declare which standards version they conform to

## Document Domains

1. **Standards** - Non-negotiable rules (naming conventions, correctness definitions)
2. **Architecture** - System-level design intent and layer contracts. The tenant section describes the substrate–tenant boundary, not the tooling (Terraform detail belongs in Deevnet Software and the tenant runbook)
3. **Roadmap** - Forward-looking shared intent (informational, not binding). Each item's milestones are a `milestones:` list in its front matter (`title`, optional `group`, `status`: done/active/planned, and for done a `date`, with `approx: true` when it is only a latest possible day), drawn in the body by `{{< milestones >}}` (`group="…"` for one heading's). **A milestone marked done gets the day it was reached as its date, in the same commit.** Roadmap progress is computed from the milestones; no `tasks_*` counts on roadmap pages or area indexes. Done milestones make the Accomplishments page (`roadmap/accomplishments.md`): Detail lists them by day, week, month, quarter or year; Summary rolls a month up by item, and a quarter or a year by area (the roadmap's top level), with each item's progress and the items finished in the period. A period can have a written account in `data/accomplishments/<period>.yaml` (`2026-10`, `2026-Q4`, `2026`): a `headline`, `bullets` (each `text` in markdown, the roadmap `items` it rolls up, by path under `docs/roadmap/` or absolute, and for a bullet about part of the period `within` that part), and optional `next` and `watch`; Summary shows it in place of the rollup. Each level is written from the one below: a month from its milestones, a quarter from its months, a year from its quarters, each more about outcomes and less about items
4. **Implementation & Tooling** (`platforms/`) - What each role runs and why, current and under evaluation; the Software Catalog; **Deevnet Software** (`platforms/deevnet-software/`: the software this site wrote itself, such as the Deevnet API, the Terraform provider and the runtime tools, one page each with what it holds and how it behaves on repair); and **Evaluations** (`platforms/evaluations/`: software items and hardware candidates, by item, revisions folded beneath). No procedures, and no restating the role: a role's page opens with one line naming the architecture role it fills (linked), then covers only the product. Roles, their network position and how they relate belong in Architecture. A role's page links to its hardware rather than describing it. **Hardware** (`platforms/hardware/`, first in the section) has one page per hardware model (`network/`, `compute/`): photo, specs, selection rationale, hosts, cabling, power, console, firmware (linked to the catalog), and its evaluation record, with revisions beneath it. Hardware facts only; no serial numbers (the repo is public)
5. **Operational Runbook** (`runbook/`) - `substrate/` for the operator (building, change and incident management with their record templates, lifecycle, network, recovery, tenant admission); `tenant/` for tenants (getting started, services, operating, recovery, Pi Lab). Tenant recovery lives under `tenant/recovery/`, not with substrate recovery
6. **Policies & Procedures** (`policies/`) - Change management, incident management, risk management (vulnerabilities, security controls, traceability, resiliency, risk register), lifecycle management (the stages from selection to retirement, with evaluation beneath it: the hardware and software criteria (each with a level, a pass condition and how to check it), process and record template. The term is **evaluation**, verdicts **Approved / Approved with conditions / Rejected / Not yet evaluated**; not "certification")
7. **Change / Incident Records** (`changes/`, `incidents/`) - Numbered records. Records, and ADRs (filed in topic folders under `architecture/decisions/<topic>/`), list **newest first**: `weight: -NNNN`, year folders `weight: -YYYY`, and new rows go at the top of each index
8. **Projects** (`content/projects/`, outside `docs/` and so outside the menu) - Active project plans: the detail behind a roadmap item (scope, reasoning, phases and their tasks, status, the change records that carry it out), written once work starts. Flat, one page per project, whatever the roadmap's areas. The roadmap item keeps only its intent and 3–8 milestones and links here; the plan links back. Plans are transient: reached only from their roadmap item. Plans keep hand-counted `tasks_*` in their front matter, recounted after each edit
9. **Completed Projects** (`completed/`) - Finished projects: a short entry for each, linking to its plan or the project's own site. When a project graduates, its plan moves to `content/projects/archive/` unchanged but for its roadmap link, which goes, and it takes the roadmap item's `milestones:` list into its front matter, with `area:` naming the roadmap area it left, so Accomplishments keeps them (a Completed Projects entry may carry `milestones:` the same way); its roadmap item is removed, and the entry is added here
10. **Platforms Integration** - How docs integrate into developer workflow
11. **Appendix** (`appendix/`) - Background primers (cryptography and PKI first). Explanatory, not normative: the rules stay in Architecture and Standards, the procedures in the Runbook

## Skills

Three skills in `.claude/skills/` carry this repository's routines, with their scripts:

- **`hugo-docs`** builds and checks the site: Hugo's own exit code, warnings new against `main`, internal links and anchors, and old URLs kept. Run it before every pull request.
- **`roadmap-update`** keeps the roadmap and plans true as work happens: milestones marked done with their dates, plans' counts recounted, plans written when work starts, and projects graduated.
- **`accomplishments`** drafts a period's written account (a month from its milestones, a quarter from its months, a year from its quarters), catches the roadmap and every account up at any time, and backfills milestones from the history of every Deevnet repository. A scheduled run on the 1st of each month runs the catch-up as a pull request.

## To revisit

- **Time boundaries on roadmap milestones** (noted 2026-11-01; revisit around 2027-02, once the
  Projects split has settled): done milestones now carry the day they were reached; still open
  is whether planned ones get target quarters or dates, and how the roadmap shows them.
- **Whether plans are searched**: plans and the archive are in site search today; one
  `bookSearchExclude: true` per page takes them out.

## Usage by Other Repos

Other Deevnet repositories include this as a Git submodule at `docs/deevnet/` and reference standards by version.

## Documentation Guidelines

- **No "See Also" sections**: Cross-references are unstable during active development. Focus on content, not links.
- **No closing Summary sections**: state a page's model in its opening paragraph instead. A recap at the end repeats the page and drifts from it.
- **Lead with what is**: a page, and each section, describes what exists today first; never open with the future. A gap worth naming comes after, briefly, and links to a roadmap item (create one if none exists).
- **Short headings, full-sentence bold lead-ins**: section headings show in the page's table of contents, so keep them to the main point in a few words ("What you need", "Raspberry Pi 4", "Finishing up"). Each section then opens with a bold lead-in that states its point as a full sentence that stands on its own, so a page can be read by its headings and bold text alone. Write "**For maximum integrity, the Root CA and every Site CA are generated and kept offline.**", not "Why the top two are offline"; "**One Deevnet Root CA serves every site.**", not "Why one root for every site". No "Why…" questions that leave the answer to the paragraph, and no bold lead-in that is a bare label ("Loss.", "Renewal.")
- **Placeholder sections OK**: Create structure with TBD/placeholder content to establish document organization.
- **Versions live in the Software Catalog** (`content/docs/platforms/software-catalog.md`), the system of record. Elsewhere, name the software and link to the catalog instead of stating a version. Keep a version only where the context needs it: change and incident records (what was true at the time), a behaviour tied to a version, a minimum requirement, or a literal value in a procedure (a firmware chain, an image tag). A change that upgrades something updates the catalog.
