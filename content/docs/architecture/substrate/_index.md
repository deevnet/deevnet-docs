---
title: "Substrate"
weight: 2
bookCollapseSection: true
---

# Substrate Architecture

Within a site, the **substrate** provides the shared infrastructure foundation — networking, compute, and services, all defined as code. The substrate is stateless — all configuration lives in source control and is applied through automation, so it can be reprovisioned from scratch at any time.

For site definitions and the independence model, see [Architecture](/docs/architecture/).

---

## Infrastructure Layers

{{< mermaid >}}
block-beta
    columns 2
    hdr["Substrate Infrastructure"]:2
    net["Network"]:1 netd["Routing · Firewall · DNS · DHCP · NAT · Switching · Wireless"]:1
    cmp["Compute · Storage¹"]:1 cmpd["Hypervisors · Persistent storage"]:1
    mgp["Management Plane"]:1 mgpd["Network management · Substrate observability"]:1
    ctp["Control Plane"]:1 ctpd["Deevnet API · Tenant DNS · Secrets · Broker"]:1
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

**Compute** is the virtualization hosts: a management hypervisor carrying both planes' VMs, and a
tenant hypervisor carrying the fabric and what runs on it. See [Compute](compute/).

**Storage**¹ is shared and persistent storage for substrate consumers. See [Storage](storage/).

### Management Plane

What the substrate runs so it can **manage and observe itself** — network device management and
substrate observability, on the management segment, for operators and substrate hosts. See
[Management Plane](management-plane/).

### Control Plane

What the substrate runs so it can **serve what runs on it** — the Deevnet API that creates tenants,
tenant DNS, the secret store, tenant observability, and the device broker. It sits on the Platform
and IoT Backend segments, because tenants and devices must never reach the management segment. See
[Control Plane](control-plane/).

The two planes are separated by **audience**, not by technology, and no host belongs to both. That
separation is what lets a tenant depend on the substrate without the substrate coming to contain
the tenant.

---

## Child Documents

- [Networking](networking/) — Networking services: DNS, DHCP, firewall, VLAN routing, switching
- [Compute](compute/) — Virtualization and compute model
- [Storage](storage/) — Shared and persistent storage
- [Management Plane](management-plane/) — How the substrate manages and observes itself
- [Control Plane](control-plane/) — How the substrate serves the tenants and devices on it
