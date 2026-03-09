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
        }

        subgraph cluster_tenant {
            label="Tenant"
            style=filled
            fillcolor="#fff3cd"

            TenantHV [label="Tenant\nCompute"]
            PiCompute [label="Pi Compute\nEdge / IoT"]
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

The platform is organized around three architectural concepts: **sites**, **substrates**, and **tenants**. A **site** is a self-contained infrastructure boundary — an independent deployment that can be built, operated, and torn down without affecting any other. Within each site, the **substrate** provides the shared infrastructure foundation (networking, compute, management plane), and **tenants** run the workloads (applications and services). This separation means infrastructure can be rebuilt or replaced independently of the services it hosts, and workloads can move between sites without being coupled to any one environment.

## Site Definitions

| Site | Purpose | Address Block |
|------|---------|---------------|
| **dvnt** | Production home infrastructure (always-on, stable) | 10.10.0.0/16 |
| **dvntm** | Mobile/portable lab for development, testing, and demos | 10.20.0.0/16 |

Each site:
- Has its own IP address space and routing
- Operates independently (can function without the other)
- Contains a complete infrastructure stack (management plane, network, compute)
- Has its own DNS zone (`dvntm.deevnet.net`, `dvnt.deevnet.net`)

### [Substrate](substrate/)

Within a site, the substrate provides the shared infrastructure foundation. The [Substrate Architecture](substrate/) section covers infrastructure layers, networking, management plane, and the builder provisioning model.

### [Tenant](tenant/)

A **tenant** is a logical workload namespace representing an application or service domain.

Examples: `grooveiq`, `vintronics`, `moneyrouter`

Tenants live **within** sites, not defining them:
- [Networking](tenant/networking/) — Tenant network isolation and VLAN model
- [Management](tenant/management/) — Tenant lifecycle and observability
- [Building](tenant/building/) — Tenant provisioning

---

## Standards

Design principles, correctness invariants, and infrastructure rules are defined in [Standards](/docs/standards/):

- [Correctness](/docs/standards/correctness/) — What it means for infrastructure to be correct
- [Identity vs Intent](/docs/standards/identity-vs-intent/) — Separation of host identity from workload intent
- [Naming](/docs/standards/naming/) — How systems and services are named
