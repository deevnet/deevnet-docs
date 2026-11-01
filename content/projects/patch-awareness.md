---
title: "Patch Awareness"
aliases:
  - /docs/projects/patch-awareness/
weight: 10
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 6
---

# Patch Awareness

Knowing when something needs a patch: new releases and security advisories for what the substrate
runs, versions that have fallen behind or reached end of life, and a feed that says so. Applying a
patch is routine operations, not a roadmap item.

**Roadmap item:** [Patch Awareness](/docs/roadmap/infrastructure/substrate/patch-awareness/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

[Software Discovery](/docs/roadmap/infrastructure/substrate/software-discovery/) says what is
running. This says when that needs attention: a release or advisory has been published for it, it
is behind, or its line is ending. One feed gathers it, so nothing depends on someone remembering to
look.

**In Scope**
- Release and advisory sources for every catalog item, watched in one place
- CVEs and vendor advisories matched against what is running
- Outdated versions and end-of-life lines surfaced, with a date
- A notification feed, so a needed patch is told rather than found

**Out of Scope**
- Applying patches, maintenance windows, rollback: routine operations, outside the roadmap
- Tenants' own software: what a tenant runs is the tenant's to track

---

## Release and advisory sources ⏳

The other half of discovery: hearing about new versions from the place that publishes them.

- ⏳ Record each catalog item's **release source** and **advisory source**, as two new catalog
  columns. For OPNsense, one entry covers its bundled services too.
- ⏳ Watch them: one place that gathers every source (feeds where they exist, a checked list where
  they don't), with each source's last-seen release.
- ⏳ Triage each new release as Discovery defines it (patch, new line, end of life, archived,
  advisory, or nothing relevant), and record the outcome, so nothing is triaged twice.
- ⏳ Record end-of-life dates for the lines in use, and surface any within six months.

---

## Notification ⏳

- ⏳ One feed of what needs attention: a new advisory affecting a running version, a release behind
  by a line, an end of life within six months
- ⏳ Delivered where the operator already looks (the alerting stack, Extended Management Plane)
