---
title: "🏗️ Architecture"
weight: 1
bookCollapseSection: true
---

# Architecture

The **Deevnet platform** is a collection of physical and virtual infrastructure — routing, switching, wireless, DNS, DHCP, NAT, WAN uplink, compute, and virtualization — provisioned entirely through Infrastructure as Code and Configuration as Code. Every device, service, and network segment is defined in source control and applied via automation, making the platform fully reproducible and rebuildable from scratch.

---

## Design Philosophy

Deevnet's infrastructure architecture is inspired by patterns used in large-scale cloud platforms —
infrastructure boundaries, automation-first provisioning, and tenant isolation — applied not to
global regions but to independent infrastructure sites, each built, operated and reprovisioned
entirely from code.

The principles, site model and layers on these pages are written for any Deevnet site. This
documentation describes one of them, the Mobile Factory, a portable site; the
[Decision Records](decisions/) are its decisions.

---

## System Overview

{{< graphviz >}}
digraph architecture {
    graph [
        rankdir=TB,
        splines=ortho,
        compound=true,
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
        labeljust=l
        margin=24
        style=filled
        fillcolor="#d0e8d0"

        subgraph cluster_substrate {
            label="Substrate"
            labeljust=l
            margin=16
            style=filled
            fillcolor="#e0f0ff"

            CoreRouter [label="Core Router\nDNS, DHCP, Firewall", width=3.2]
            WirelessAP [label="Wireless AP", width=1.0]
            AccessSwitch [label="Access Switch", width=6.0]

            // The AP trunks into the access switch, not the router. Pinned to
            // the same rank so the edge draws as a straight run across, and
            // kept inside this cluster so it stays in the substrate.
            { rank=same; AccessSwitch -> WirelessAP }

            // The Pi lab: physical hosts the substrate inventories and cables,
            // lent to tenant projects. Outside the yellow hypervisor boxes
            // because it is not virtualized.
            PiCompute [label="Pi Lab\nbare-metal, lent to tenants"]

            // Yellow boxes are virtual: each is a hypervisor (standalone
            // today, could grow into a cluster)
            subgraph cluster_mgmt {
                label="Shared Services"
                labelloc=b
                labeljust=l
                style=filled
                fillcolor="#fff3cd"

                SubstrateSvc [label="Substrate Services\nnetwork mgmt, observability"]
                SharedTenantSvc [label="Tenant Services\nprovisioning API, DNS, secrets, broker"]
            }

            subgraph cluster_tenant {
                label="Tenant"
                labelloc=b
                labeljust=l
                style=filled
                fillcolor="#fff3cd"

                TenantHV [label="Tenant\nCompute"]
            }
        }

        // Edge devices are neither substrate nor tenant: they sit in the
        // site, attached to the substrate's access networks.
        EdgeDev [label="Edge Devices\nwireless\napplication-owned, platform-attached"]

        CoreRouter -> AccessSwitch
        AccessSwitch -> PiCompute
        // One uplink per hypervisor: lhead clips the edge at the cluster
        // border so it stops at the box rather than reaching a node inside.
        AccessSwitch -> SubstrateSvc [lhead=cluster_mgmt]
        AccessSwitch -> TenantHV [lhead=cluster_tenant]
        // Attachment is wireless, and the box says so. The edge is kept but
        // invisible: without it the node has no constraints at all and dot
        // floats it to the top of the site.
        WirelessAP -> EdgeDev [minlen=2, style=invis]
    }

    EdgeRouter -> CoreRouter
    Builder -> AccessSwitch
}
{{< /graphviz >}}

Yellow boxes are virtual, each on its own hypervisor. Everything else inside the substrate is
physical. Edge devices sit inside the site but outside the substrate.

---

## Substrate and Tenant

A **site** is one self-contained deployment: its own address space, DNS zone and hardware. Within
it, the architecture draws one main line — between the infrastructure and what runs on it.

- **[Substrate](substrate/)** — the site's infrastructure: network, compute, storage, and the
  management and control planes. Built and rebuilt from code by the operator.
- **[Tenant](tenant/)** — an isolated slice of the site for one application: its own network, DNS
  zone and workloads, built for it by the substrate when it asks.
- **[Edge devices](edge-devices/)** — physical things an application owns, which the substrate
  attaches to an access network. Neither substrate nor tenant, and never inside a tenant's network.
- **[Builder](builder/)** — the portable server that creates a site's substrate from scratch, then
  hands authority to it.

## Going deeper

- [Network Segmentation](network-segmentation/) — the segments, their trust levels and the policy
  between them
- [Naming and Addressing](naming-and-addressing/) — the site address plan, and how hosts and
  tenants get addresses and names
- [Decision Records](decisions/) — why each choice was made
- [Resiliency & Limits](/docs/policies/risk-management/resiliency/) — what the hardware can't do,
  and why the site is built to be rebuilt rather than to stay up
