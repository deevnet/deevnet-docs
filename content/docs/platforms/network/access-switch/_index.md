---
title: "Access Switch"
weight: 3
---

# Access Switch

## Purpose

The access switch provides **Layer 2 connectivity** for substrate hosts, connecting endpoints to the core router. Access switches handle VLAN tagging, port isolation, and traffic aggregation.

{{< mermaid >}}
graph LR
    A[Core Router] <--> B[Access Switch] <--> C[Site Hosts]
{{< /mermaid >}}

---

## Hardware

[TP-Link Omada SG2218](/docs/hardware/network/tp-link-sg2218/): specs, the port map, power and console.

---

## Management

| Attribute | Value |
|-----------|-------|
| **Controller** | TP-Link Omada SDN |
| **CLI** | SSH access |
| **Web UI** | Standalone or controller-managed |
| **Automation** | Omada API via `deevnet.net` collection |

## Roles

| Role | Description |
|------|-------------|
| **L2 switching** | Connects substrate hosts to core router |
| **VLAN tagging** | 802.1Q trunk to core router |
| **Port isolation** | Separates trust zones at L2 |


---

## Configuration Management

| Controller | Automation |
|------------|------------|
| None: standalone, not yet adopted into Omada ([CHG-0009](/docs/changes/2026/0009-access-switch-adoption/), on hold) | `deevnet.net` `switch_vlans` over SSH CLI |

### VLAN Configuration

VLANs are defined in the substrate standards and configured on all access switches:

| VLAN | Purpose |
|------|---------|
| Management | Infrastructure management traffic |
| Tenant | Application/user traffic |
| IoT | Isolated IoT devices |

Specific VLAN IDs are documented in the [Network Segmentation](/docs/standards/network-segmentation/) standard.
