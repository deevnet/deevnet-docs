---
title: "Builder & Core Services"
weight: 1
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 0
---

# Builder & Core Services

Builder infrastructure, network automation, and core services required to provision and rebuild the dvnt (home) site from bare metal.

The dvnt site is a permanent, always-on installation using the AOOSTAR N1 PRO as a dedicated provisioning node. It uses the same automation as dvntm with site-specific inventory (10.10.x.0/24 addressing).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Achieve fully automated, repeatable provisioning of the dvnt (home) site from bare metal to running core services, reusing the automation built for dvntm with dvnt-specific inventory.

**In Scope**
- Bare-metal provisioning (PXE, Ansible) using dvnt inventory
- Network infrastructure automation (switching, wireless, routing)
- Full air-gap rebuild capability
- dvnt-specific hardware (AOOSTAR N1 PRO provisioner, site networking gear)

**Out of Scope**
- Extended management plane — see [Extended Management Plane](../management-plane/)
- Patch automation — see [Patch Automation](../patch-automation/)
- Full site rebuild event — see [Full Site Rebuild](../full-rebuild/)
