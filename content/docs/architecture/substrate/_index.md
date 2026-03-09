---
title: "Substrate"
weight: 1
bookCollapseSection: true
---

# Substrate Architecture

Within a site, the **substrate** provides the shared infrastructure foundation — networking, compute, and services, all defined as code. The substrate is stateless — all configuration lives in source control and is applied through automation, so it can be reprovisioned from scratch at any time.

For site definitions (dvnt, dvntm) and the independence model, see [Architecture](../).

---

## Infrastructure Layers

{{< mermaid >}}
block-beta
    columns 2
    block:infra:2
        columns 2
        hdr["Substrate Infrastructure"]:2
        core["Core Services"]:1 cored["Network · Compute · Storage¹"]:1
        ext["Extended Services"]:1 extd["Observability · Automation · Access"]:1
    end
    style hdr text-align:left
{{< /mermaid >}}

¹ Storage is a planned future addition to core services.

### Core Services

The foundational infrastructure that must survive loss of all other tiers:

**Network** — Connectivity, segmentation, and foundational network services:
- **Routing and gateway** — NAT, inter-segment routing, upstream connectivity
- **Firewall** — Segment isolation and egress policy
- **DNS** — Authoritative resolution for the substrate zone
- **DHCP** — Static mappings for known hosts, dynamic pools per segment
- **Switching and wireless** — VLAN trunking and wireless access

**Compute** — Virtualization hosts for management-plane and tenant workloads:
- Extended services (observability, automation, access)
- Tenant application VMs

**Storage**¹ — Shared and persistent storage for substrate consumers.

See [Networking](networking/) for the network segmentation model.
See [Core Services](management-plane/core-services/) for core platform details.

### Extended Services

Additive services providing observability, automation, and access — runs on the management hypervisor:
- Centralized logging and metrics
- Automation runners and CI/CD
- Jump hosts and access tooling

See [Management Plane](management-plane/) for how these services are provisioned and managed.
See [Extended Services](management-plane/extended-services/) for extended management services.

---

## Child Documents

- [Networking](networking/) — Network segmentation and VLAN model
- [Addressing](addressing/) — IP addressing convention and subnet model
- [Management Plane](management-plane/) — Management plane overview, core and extended services
