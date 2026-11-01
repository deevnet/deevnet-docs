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

## Replacement ⏳

- ⏳ Choose the hardware: the [N100 Router Appliance](/docs/platforms/evaluations/hardware/n100-router-appliance/) is the candidate under evaluation
- ⏳ Build it from code and swap it in under a change record, the ZimaBoard kept to put back
- ⏳ Prove it under load: a multi-gigabyte transfer and a full deploy through it, with no hang and no watchdog timeout
- ⏳ Close INC-0004
