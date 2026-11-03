---
title: "Credential Rotation"
bookCollapseSection: true
aliases:
  - /docs/roadmap/infrastructure/credential-rotation/
weight: 10
value: [secure-by-default]
waypoints:
  - title: "Exposed credentials rotated; every public repository scanned on push (CHG-0035)"
    status: done
    date: "2026-10-06"
  - title: "Every long-lived credential listed, with what it unlocks and what uses it"
    status: done
    date: "2026-11-03"
  - title: "A written rotation procedure for each kind of credential, naming everything that must change with it"
    status: planned
  - title: "Static credentials assessed for short lifetimes, and the ones that cannot be shortened recorded"
    status: planned
  - title: "A stated policy for what counts as an exposed credential and what happens next"
    status: planned
---

# Credential Rotation

Define how a credential gets replaced. The [Secure Identity Standard](/docs/standards/secure-identity/) already says credentials should be short-lived; nothing says how to make one short-lived, or what to do when a specific one is exposed.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Credential Rotation](/docs/roadmap/infrastructure/substrate/credential-rotation/plan/)
