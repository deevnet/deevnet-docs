---
title: "Architecture"
weight: 1
bookCollapseSection: true
---

# Architecture

The **Deevnet platform** is a collection of physical and virtual infrastructure — routing, switching, wireless, DNS, DHCP, NAT, WAN uplink, compute, and virtualization — provisioned entirely through Infrastructure as Code and Configuration as Code. Every device, service, and network segment is defined in source control and applied via automation, making the platform fully reproducible and rebuildable from scratch.

---

## Design Philosophy

Deevnet's infrastructure architecture is inspired by patterns used in large-scale cloud platforms. Concepts such as infrastructure boundaries, automation-first provisioning, and tenant isolation are intentionally applied.

However, Deevnet operates at a much smaller scale than hyperscale cloud providers. Instead of modeling multiple global regions and availability zones, the architecture focuses on independent infrastructure sites that can be built, operated, and reprovisioned entirely from code.

This approach preserves the architectural principles of cloud infrastructure while remaining practical for a home and portable lab environment.

---

## System Overview

{{< graphviz >}}
digraph architecture {
    graph [
        rankdir=TB,
        splines=ortho,
        nodesep=0.6,
        ranksep=0.8,
        fontname="Helvetica",
        bgcolor="#e0e0e0",
        pad=0.15,
        size="6.5,10!"
    ]
    node [shape=box, style="rounded,filled", fillcolor=white, fontname="Helvetica"]
    edge [arrowsize=0.7, fontname="Helvetica"]

    // Top row - force same rank for Edge Router and Builder
    Internet [label="Internet/Upstream LAN", width=2.5]
    EdgeRouter [label="Edge Router"]
    Builder [label="Builder"]

    Internet -> EdgeRouter
    { rank=same; EdgeRouter; Builder }
    EdgeRouter -> Builder [minlen=2]

    subgraph cluster_site {
        label="Site"
        style=filled
        fillcolor="#d0e8d0"

        subgraph cluster_substrate {
            label="Substrate"
            style=filled
            fillcolor="#e0f0ff"

            CoreRouter [label="Core Router\nDNS, DHCP, Firewall", width=2.5]
            WirelessAP [label="Wireless AP", width=1.0]
            AccessSwitch [label="Access Switch", width=4.5]
            MgmtHV [label="Extended\nServices", width=2.2]

            subgraph cluster_tenant {
                label="Tenant"
                style=filled
                fillcolor="#fff3cd"

                TenantHV [label="Tenant\nCompute"]
                PiCompute [label="Pi Compute\nEdge / IoT"]
            }
        }

        CoreRouter -> WirelessAP
        CoreRouter -> AccessSwitch
        AccessSwitch -> MgmtHV
        AccessSwitch -> TenantHV
        AccessSwitch -> PiCompute
    }

    EdgeRouter -> CoreRouter
    Builder -> AccessSwitch
}
{{< /graphviz >}}

The platform is organized around three architectural boundaries — **sites**, **substrates**, and **tenants** — that separate infrastructure from workloads. The hardware substrate within each site can be rebuilt or replaced without affecting the workloads running on it, and workloads can be deployed to any site without being coupled to a specific environment.

## Sites

A **site** is an independent infrastructure deployment with its own IP address space, DNS zone, and complete hardware stack. Each site can be built, operated, and torn down without affecting any other.

| Site | Purpose | Address Block | DNS Zone |
|------|---------|---------------|----------|
| **dvnt** | Production home infrastructure (always-on, stable) | 10.10.0.0/16 | dvnt.deevnet.net |
| **dvntm** | Mobile/portable lab for development, testing, and demos | 10.20.0.0/16 | dvntm.deevnet.net |

### [Substrate](substrate/)

The **substrate** is the shared infrastructure foundation within a site — networking, compute, storage, and management plane. It provides the base that workloads run on, but can be rebuilt or replaced independently of them. Covers infrastructure layers, the builder provisioning model, and authority modes.

### [Network Segmentation](network-segmentation/)

The network segmentation model that divides each substrate into isolated broadcast domains, enforcing trust boundaries and traffic separation at the network layer. Defines nine segment types, trust hierarchy, default routing policy, and authority mode transitions.

### [Addressing](addressing/)

The IP addressing convention for Deevnet sites. Covers VLAN-based subnets, host ranges, gateway conventions, and WAN operation modes.

### [Tenant](tenant/)

A **tenant** is an isolated workload boundary for applications and services running on a site's substrate. Tenants are decoupled from the underlying infrastructure — they can be provisioned, migrated, or rebuilt without changes to the substrate, and are not bound to any one site. Covers tenant networking, lifecycle management, and provisioning.
