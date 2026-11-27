---
title: "Declarative Reconciliation"
bookCollapseSection: true
aliases:
  - /docs/roadmap/infrastructure/mobile/reconciliation/
weight: 4
value: [one-operator]
waypoints:
  - title: "Leftover DHCP reservations, DNS records and boot files from deleted hosts removed"
    added: "2026-11-01"
    status: planned
  - title: "Automation removes a host's DHCP, DNS and boot entries when it leaves inventory"
    added: "2026-11-01"
    status: planned
  - title: "Network settings that exist only on the running router declared in code"
    added: "2026-11-01"
    value: [rebuild-from-code]
    status: planned
  - title: "A read-only report of live network state with no matching declaration"
    added: "2026-11-01"
    value: [no-surprises]
    status: planned
---

# Declarative Reconciliation

Close the gap between what inventory declares and what the substrate actually runs. Several roles today reconcile *additively* — they create and update, but never remove — so deleting a host from inventory leaves its live state behind indefinitely.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Declarative Reconciliation](/docs/roadmap/infrastructure/substrate/reconciliation/plan/)
