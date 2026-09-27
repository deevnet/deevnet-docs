---
title: "Access Switch"
weight: 3
---

# Access Switch

Fills the **access switch** role — see [Substrate Networking → Switching](/docs/architecture/substrate/networking/#switching).

---

## Hardware

[TP-Link Omada SG2218](/docs/platforms/hardware/network/tp-link-sg2218/): specs, the port map, power and console.

---

## Management

| Attribute | Value |
|-----------|-------|
| **Controller** | None: standalone, not yet adopted into Omada ([CHG-0009](/docs/changes/2026/0009-access-switch-adoption/), on hold) |
| **CLI** | SSH |
| **Web UI** | Standalone |
| **Automation** | `deevnet.net` `switch_vlans` over the SSH CLI |

Which VLANs exist, and which ports carry them, come from inventory. The segments are described in
[Network Segmentation](/docs/architecture/network-segmentation/); their IDs and subnets are in the
[Network Reference](/docs/runbook/substrate/network/network-reference/), and the port assignments in
the hardware page's port map.
