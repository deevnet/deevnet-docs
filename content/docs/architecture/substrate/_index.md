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
    columns 1
    block:infra["Substrate Infrastructure"]
        columns 2
        net["Network"]:1 netd["Routing, firewall, DNS, DHCP, switching, wireless"]:1
        svc["Services"]:1 svcd["Core (DNS, DHCP, firewall) · Extended (observability, automation, access)"]:1
        comp["Compute"]:1 compd["Virtualization hosts for management-plane and tenant workloads"]:1
    end
{{< /mermaid >}}

### Network

The network layer provides connectivity, segmentation, and foundational services for the substrate:

- **Routing and gateway** — NAT, inter-segment routing, upstream connectivity
- **Firewall** — Segment isolation and egress policy
- **DNS** — Authoritative resolution for the substrate zone
- **DHCP** — Static mappings for known hosts, dynamic pools per segment
- **Switching and wireless** — VLAN trunking and wireless access

See [Networking](networking/) for the network segmentation model.

### Core Services

Foundational services that must survive loss of all other tiers:
- DNS authority model and naming
- DHCP, NAT, firewall
- Provided by network infrastructure in production

### Extended Services

Additive services providing observability, automation, and access — runs on the management hypervisor:
- Centralized logging and metrics
- Automation runners and CI/CD
- Jump hosts and access tooling

See [Management Plane](management-plane/) for how these services are provisioned and managed.
See [Core Services](management-plane/core-services/) for core platform details.
See [Extended Services](management-plane/extended-services/) for extended management services.

### Compute

Virtualization hosts run management-plane and tenant workloads as VMs:
- Extended services (observability, automation, access)
- Tenant application VMs

---

## Child Documents

- [Networking](networking/) — Network segmentation and VLAN model
- [Addressing](addressing/) — IP addressing convention and subnet model
- [Management Plane](management-plane/) — Management plane overview, core and extended services
