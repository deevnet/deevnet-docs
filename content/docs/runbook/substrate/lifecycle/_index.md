---
title: "Lifecycle"
weight: 4
bookCollapseSection: true
aliases:
  - /docs/runbook/lifecycle/
---

# Lifecycle

Keeping what is in service current, and taking it out of service when its time comes.

- [Patching](patching/) — day-2 maintenance and system updates
- [Patch Tools for Claude](patch-tools-for-claude/) — asking Claude what needs patching, through read-only MCP tools on the Builder
- [Inventory Lifecycle](inventory-lifecycle/) — asset tracking and decommissioning
- [Omada Controller Upgrade](omada-controller-upgrade/) — upgrading the network controller in place, keeping its data
- [Shutdown and Power-On](shutdown-and-power-on/) — powering the site down in order, and what runs, and what waits, once it is back on
- [Renaming Hosts](host-rename/) — what any rename has to reckon with, and renaming a Proxmox node
- [SSH Host Keys](host-keys/) — every host's SSH keys recorded in git and trusted by the builders, and what to do when a host is rebuilt

Each upgrade is a change of type **Upgrade**, and gets a
[change record](/docs/runbook/substrate/change-management/change-record-template/).
