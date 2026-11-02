---
title: "Core Router Uplift"
bookCollapseSection: true
weight: 2
value: [no-surprises]
milestones:
  - title: "Replacement core router hardware chosen (the N100 Router Appliance is the candidate)"
    status: planned
  - title: "New core router built from code and swapped in, the old ZimaBoard kept to put back"
    status: planned
  - title: "New core router proven under a multi-gigabyte transfer and a full deploy"
    status: planned
  - title: "The core router hang incident (INC-0004) closed"
    status: planned
---

# Core Router Uplift

The mobile site's core router is a ZimaBoard 832. It hangs under large transfers: a hard hang during a
log store deploy, then recurring `re0` watchdog timeouts
([INC-0004](/docs/incidents/2026/0004-core-router-lost/)). It is replaced by hardware that carries
them.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Core Router Uplift](/docs/roadmap/site-work/mobile/core-router-uplift/plan/)
