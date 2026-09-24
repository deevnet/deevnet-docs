---
title: "Network"
weight: 3
bookCollapseSection: true
aliases:
  - /docs/runbook/network/
---

# Network

Reference and day-2 procedures for the site network.

- [Important URLs](important-urls/) — every management interface and service endpoint, by DNS name and by IP
- [Operator Access](operator-access/) — the three ways in: trusted Wi-Fi day to day, the travel router when the switch is down, the operator port as a last resort
- [Segment Check](segment-check/) — from a laptop on each SSID, confirm the segment reaches what policy allows and nothing else
- [Network Reference](network-reference/) — VLAN assignments, subnets, gateways and DHCP ranges for each site

Building the network from scratch is part of [Building Infrastructure](/docs/runbook/substrate/building-recovery/build-network/).
Upgrading the Omada controller is under [Lifecycle](/docs/runbook/substrate/lifecycle/omada-controller-upgrade/), and recovering it
under [Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/).
