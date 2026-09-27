---
title: "Recovery"
weight: 4
bookCollapseSection: true
aliases:
  - /docs/runbook/recovery/
---

# Recovery

Getting service back when something has failed.

- [Console Recovery](console-recovery/) — getting back into a device when the network cannot reach it: core router, hypervisors, access switch and AP
- [Omada Controller Recovery](omada-controller-recovery/) — restoring the network controller from a data snapshot, including falling back from a bad upgrade
- [Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/) — reinstalling the hardware Builder from a temporary builder VM, when it is lost or needs a clean install

Rebuilding a site or a host from nothing is covered by [Building Infrastructure](/docs/runbook/substrate/building-recovery/). What happened in past failures is under [Incident Records](/docs/incidents/).
