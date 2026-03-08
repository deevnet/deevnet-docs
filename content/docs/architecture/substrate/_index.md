---
title: "Substrate"
weight: 1
bookCollapseSection: true
---

# Substrate Architecture

A **substrate** is an infrastructure environment—a self-contained network with its own compute, storage, and management plane.

---

## Substrate Definitions

| Substrate | Purpose | Address Block |
|-----------|---------|---------------|
| **dvnt** | Production home infrastructure (always-on, stable) | 10.10.0.0/16 |
| **dvntm** | Mobile/portable lab for development, testing, and demos | 10.20.0.0/16 |

Each substrate:
- Has its own IP address space and routing
- Operates independently (can function without the other)
- Contains a complete infrastructure stack (management plane, network, compute)
- Has its own DNS zone (`dvntm.deevnet.net`, `dvnt.deevnet.net`)

The same builder can move between substrates—it provisions whichever environment it's connected to.

---

## Infrastructure Layers

{{< mermaid >}}
block-beta
    columns 1
    block:infra["Substrate Infrastructure"]
        columns 2
        mp["Management Plane"]:1 mpd["Builder (provisioning, artifacts, PXE/TFTP)"]:1
        net["Network"]:1 netd["Core Router (gateway, firewall, DNS, DHCP), switches, APs"]:1
        comp["Compute"]:1 compd["Compute hosts, Raspberry Pis, embedded devices"]:1
    end
{{< /mermaid >}}

### Management Plane

The management plane consists of core infrastructure services and optional virtual management services:

**Builder** — The out-of-band provisioning role that builds everything else:
- Artifact hosting, PXE/TFTP, Ansible controller
- Portable across substrates, air-gapped capable
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

The **Core Router** is the production network authority:
- Firewall and NAT gateway
- Authoritative DNS for substrate zone
- DHCP with static mappings
- Inter-segment routing with VLAN isolation

See [Networking](networking/) for the network segmentation model.

### Compute

**Compute hosts** provide virtualized workloads:
- Management-plane VMs (observability, automation, access)
- Tenant application VMs

**Raspberry Pis and embedded devices** handle edge workloads:
- SDR, IoT gateways, sensors

---

## Authority Modes

Substrate provisioning uses **explicit authority transitions**:

| Mode | DNS/DHCP Authority | When |
|------|-------------------|------|
| **Bootstrap-authoritative** | Builder (dnsmasq) | During initial provisioning |
| **Router-authoritative** | Core Router | Production operation |

The transition is explicit—once the Core Router is configured and validated, the builder stops serving DNS/DHCP and becomes a regular admin host.

See [Core Services](management-plane/core-services/) for details on authority models.

---

## Child Documents

- [Networking](networking/) — Network segmentation and VLAN model
- [Addressing](addressing/) — IP addressing convention and subnet model
- [Management Plane](management-plane/) — Management plane overview, core and extended services
