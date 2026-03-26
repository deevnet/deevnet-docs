---
title: "Full Site Rebuild"
weight: 4
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 6
---

# Full Site Rebuild

End-to-end rebuild of the dvntm site from scratch. Validates air-gap recovery capability and exercises all automation built across the Builder, Patch Automation, and Extended Management Plane projects.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Perform a complete tear-down and rebuild of the dvntm (mobile) site to validate that the infrastructure-as-code automation is truly end-to-end. This is the capstone event that proves the system works.

**In Scope**
- Full substrate rebuild (builder, core router, switch, AP, hypervisors)
- Timing and gap collection during rebuild
- Iterative fixes until all steps are accounted for
- Coordinated release tagging across all deevnet repos

**Prerequisites**
- [Builder & Core Services](../builder/) — ✅ Complete
- [Patch Automation](../patch-automation/) — firmware and automation improvements applied
- [Extended Management Plane](../management-plane/) — management services deployable

---

## Full Site Rebuild Event ⏳

- ⏳ Read and analyze the build/recovery plan
- ⏳ Rebuild the builder node (no version bump)
- ⏳ Rebuild core services (core router, access switch, AP) — collect timings, findings, and identify gaps
- ⏳ Rebuild management plane (Proxmox, extended services)
- ⏳ Apply fixes and iterate until all steps are accounted for
- ⏳ Tag all deevnet repos with a coordinated release version
