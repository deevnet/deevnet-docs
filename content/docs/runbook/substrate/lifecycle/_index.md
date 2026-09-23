---
title: "Lifecycle"
weight: 2
bookCollapseSection: true
aliases:
  - /docs/runbook/lifecycle/
---

# Lifecycle

Keeping what is in service current, and taking it out of service when its time comes.

- [Patching](patching/) — day-2 maintenance and system updates
- [Inventory Lifecycle](inventory-lifecycle/) — asset tracking and decommissioning
- [Omada Controller Upgrade](omada-controller-upgrade/) — upgrading the network controller in place, keeping its data
- [Renaming Hosts](host-rename/) — what any rename has to reckon with, and renaming a Proxmox node

Each upgrade is a change of type **Upgrade**, and gets a
[change record](/docs/policies/change-management/change-record-template/).
