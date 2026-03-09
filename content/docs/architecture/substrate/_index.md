---
title: "Substrate"
weight: 1
bookCollapseSection: true
---

# Substrate Architecture

Within a site, the **substrate** provides the shared infrastructure foundation — networking, compute, storage, and management plane, all defined as code. The substrate is stateless — all configuration lives in source control and is applied through automation, so it can be reprovisioned from scratch at any time.

For site definitions (dvnt, dvntm) and the independence model, see [Architecture](../).

The same builder can move between sites—it provisions whichever environment it's connected to.

---

## Infrastructure Layers

{{< mermaid >}}
block-beta
    columns 1
    block:infra["Substrate Infrastructure"]
        columns 2
        mp["Management Plane"]:1 mpd["Builder (provisioning, artifacts, PXE/TFTP)"]:1
        net["Network"]:1 netd["Gateway, firewall, DNS, DHCP, switching, wireless"]:1
        comp["Compute"]:1 compd["Virtualization, edge and embedded compute"]:1
    end
{{< /mermaid >}}

### Management Plane

The management plane consists of three tiers:

**Builder** — The out-of-band provisioning role that builds everything else:
- Artifact hosting, PXE/TFTP, automation controller
- Portable across sites, air-gapped capable
- Out-of-band control and recovery services

**Core Services** — Foundational services that must survive loss of all other tiers:
- DNS authority model and naming
- DHCP, NAT, firewall
- Authority transitions between builder and router

**Extended Services** — Additive services providing observability, automation, and access:
- Centralized logging and metrics
- Automation runners and CI/CD
- Jump hosts and access tooling

See [Management Plane](management-plane/) for the full management plane architecture.
See [Builder](management-plane/builder/) for the provisioning architecture.
See [Core Services](management-plane/core-services/) for core platform details.
See [Extended Services](management-plane/extended-services/) for extended management services.

### Network

The network layer provides connectivity, segmentation, and foundational services for the substrate:

- **Routing and gateway** — NAT, inter-segment routing, upstream connectivity
- **Firewall** — Segment isolation and egress policy
- **DNS** — Authoritative resolution for the substrate zone
- **DHCP** — Static mappings for known hosts, dynamic pools per segment
- **Switching and wireless** — VLAN trunking and wireless access

See [Networking](networking/) for the network segmentation model.

### Compute

**Virtualization** — Hosts management-plane and tenant workloads as VMs:
- Extended services (observability, automation, access)
- Tenant application VMs

**Edge and embedded** — Lightweight compute for IoT and signal processing:
- SDR receivers, IoT gateways, sensors

---

## Authority Modes

Substrate provisioning uses **explicit authority transitions**:

| Mode | DNS/DHCP Authority | When |
|------|-------------------|------|
| **Bootstrap** | Builder | During initial provisioning or recovery |
| **Production** | Network infrastructure | Normal operation |

The transition is explicit — only one authority is active at a time. Once production network infrastructure is configured and validated, the builder's DNS/DHCP services are disabled.

See [Core Services](management-plane/core-services/) for details on authority models.

---

## Child Documents

- [Networking](networking/) — Network segmentation and VLAN model
- [Addressing](addressing/) — IP addressing convention and subnet model
- [Management Plane](management-plane/) — Management plane overview, core and extended services
