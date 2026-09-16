---
title: "Substrate"
weight: 2
bookCollapseSection: true
---

# Substrate Architecture

Within a site, the **substrate** provides the shared infrastructure foundation — networking, compute, and services, all defined as code. The substrate is stateless — all configuration lives in source control and is applied through automation, so it can be reprovisioned from scratch at any time.

For site definitions (home, mobile) and the independence model, see [Architecture](/docs/architecture/).

---

## Infrastructure Layers

{{< mermaid >}}
block-beta
    columns 2
    hdr["Substrate Infrastructure"]:2
    net["Network"]:1 netd["Routing · Firewall · DNS · DHCP · NAT · Switching · Wireless"]:1
    cmp["Compute · Storage¹"]:1 cmpd["Hypervisors · Persistent storage"]:1
    mcp["Management / Control Plane"]:1 mcpd["Network management · Observability"]:1
{{< /mermaid >}}

¹ Shared storage is a planned future addition.

### Network

Connectivity, segmentation, and the foundational network services. Nothing else in the substrate
has to be running for these to work:
- **Routing and gateway**: NAT, inter-segment routing, upstream connectivity
- **Firewall**: segment isolation and egress policy
- **DNS**: authoritative resolution for the substrate zone
- **DHCP**: static mappings for known hosts, dynamic pools per segment
- **Switching and wireless**: VLAN trunking and wireless access

See [Networking](networking/) for substrate networking services.
See [Network Segmentation](/docs/architecture/network-segmentation/) for the segment model and trust hierarchy.

### Compute and Storage

**Compute** is the virtualization hosts: a management hypervisor for the management / control
plane, and workload hypervisors for what runs on the substrate. See [Compute](compute/).

**Storage**¹ is shared and persistent storage for substrate consumers. See [Storage](storage/).

### Management / Control Plane

The services the substrate runs on its management hypervisor to manage and observe itself:
network device management and substrate observability. See
[Management / Control Plane](management-plane/).

---

## Child Documents

- [Networking](networking/) — Networking services: DNS, DHCP, firewall, VLAN routing, switching
- [Compute](compute/) — Virtualization and compute model
- [Storage](storage/) — Shared and persistent storage
- [Management / Control Plane](management-plane/) — How the substrate manages and observes itself
