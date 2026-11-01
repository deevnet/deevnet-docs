---
title: "Extended Management Plane"
bookCollapseSection: true
aliases:
  - /docs/roadmap/infrastructure/mobile/management-plane/
weight: 2
milestones:
  - title: "Site management services grouped onto six VMs by domain (CHG-0008)"
    status: done
    date: "2026-09-16"
  - title: "Management plane requirements defined: retention, alerting, secrets access and identity"
    status: active
  - title: "Recovery copies of the network's configuration: routine Wi-Fi controller snapshots, and core router configs that survive losing the build server"
    status: planned
  - title: "Each Wi-Fi network's reach checked from a real client"
    status: done
    date: "2026-09-23"
  - title: "Automated checks that a finished build matches inventory, with a pass/fail report"
    status: active
  - title: "Nightly encrypted backups, one restore rehearsed (CHG-0039)"
    status: done
    date: "2026-10-07"
  - title: "Management plane architecture, deployment and troubleshooting documentation written"
    status: planned
---

# Extended Management Plane

The management services the mobile site runs on: the domain VMs, network management, build
verification, backups and documentation. Observability and secrets are items of their own.

- **GitHub:** https://github.com/deevnet/ansible-collection-deevnet.mgmt

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Extended Management Plane](/docs/roadmap/infrastructure/substrate/management-plane/plan/)
