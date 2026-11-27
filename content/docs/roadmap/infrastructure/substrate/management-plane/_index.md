---
title: "Extended Management Plane"
bookCollapseSection: true
aliases:
  - /docs/roadmap/infrastructure/mobile/management-plane/
weight: 2
waypoints:
  - title: "Site management services grouped onto six VMs by domain (CHG-0008)"
    added: "2026-09-16"
    value: [one-operator]
    status: done
    date: "2026-09-16"
  - title: "Management plane requirements defined: retention, alerting, secrets access and identity"
    added: "2026-11-01"
    value: [no-surprises]
    status: active
  - title: "Recovery copies of the network's configuration: the Wi-Fi controller and core router backed up after every change, where they survive losing the build server"
    added: "2026-11-11"
    value: [rebuild-from-code]
    status: done
    date: "2026-11-11"
  - title: "Each Wi-Fi network's reach checked from a real client"
    added: "2026-09-23"
    value: [no-surprises]
    status: done
    date: "2026-09-23"
  - title: "Automated checks that a finished build matches inventory, with a pass/fail report"
    added: "2026-11-01"
    value: [no-surprises]
    status: active
  - title: "Nightly encrypted backups, one restore rehearsed (CHG-0039)"
    added: "2026-10-07"
    value: [rebuild-from-code]
    status: done
    date: "2026-10-07"
  - title: "Management plane architecture, deployment and troubleshooting documentation written"
    added: "2026-11-01"
    value: [one-operator]
    status: done
    date: "2026-11-11"
---

# Extended Management Plane

The management services the mobile site runs on: the domain VMs, network management, build
verification, backups and documentation. Observability and secrets are items of their own.

- **GitHub:** https://github.com/deevnet/ansible-collection-deevnet.mgmt

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Extended Management Plane](/docs/roadmap/infrastructure/substrate/management-plane/plan/)
