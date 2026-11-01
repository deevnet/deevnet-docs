---
title: "Core Router Uplift"
weight: 2
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 4
---

# Core Router Uplift

The mobile site's core router is a ZimaBoard 832. It hangs under large transfers: a hard hang during a
log store deploy, then recurring `re0` watchdog timeouts
([INC-0004](/docs/incidents/2026/0004-core-router-lost/)). It is replaced by hardware that carries
them.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

- ⏳ Hardware chosen (the N100 Router Appliance is the candidate)
- ⏳ Built from code and swapped in, the ZimaBoard kept
- ⏳ Proven under a multi-gigabyte transfer and a full deploy
- ⏳ INC-0004 closed

**Project plan:** [Core Router Uplift](/docs/projects/core-router-uplift/)
