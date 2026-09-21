---
title: "🏗️ Architecture"
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

            // Physical substrate compute: inventoried, cabled to the access
            // switch, and outside the yellow hypervisor boxes because it is
            // not virtualized.
            PiCompute [label="Bare-Metal Compute\nsingle-board hosts"]

            // Yellow boxes are virtual: each is a hypervisor (standalone
            // today, could grow into a cluster)
            subgraph cluster_mgmt {
                label="Shared Services"
                labelloc=b
                labeljust=l
                style=filled
                fillcolor="#fff3cd"

                SubstrateSvc [label="Substrate Services\nnetwork mgmt, observability"]
                SharedTenantSvc [label="Tenant Services\nDeevnet API, DNS, secrets, broker"]
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

Yellow boxes are virtual: each runs on its own hypervisor, standalone today but able to grow into a cluster. Everything else inside the substrate is physical — including bare-metal compute, which is inventoried, cabled to the access switch, and provisioned like any other substrate host. Edge devices sit inside the site but outside the substrate: the substrate attaches them, it does not own them.

The platform is organized around a few architectural boundaries that separate infrastructure from what runs on it. A **site** is a self-contained deployment. Within it, the **substrate** provides infrastructure — networking, virtualized compute, and bare-metal hosts alike; **tenants** are isolated virtual workloads that run on it; and **edge devices** are physical things an application owns and the platform attaches. Because infrastructure is fully defined in code, a substrate can be reprovisioned from scratch and workloads redeployed to it — or to a different site entirely — without being coupled to any specific hardware.

The distinction between the last two matters more than it first appears. A tenant is virtual and lives in an overlay of its own; an edge device is physical, shares an access network with devices of other owners, and is **never** a member of its application's network. Keeping them separate is what lets an application own a device without the substrate owning it, and without the device gaining reach into its application's network.

## Sites

A **site** is an independent infrastructure deployment with its own IP address space, DNS zone, and complete hardware stack. Each site can be built, operated, and torn down without affecting any other.

| Site | Purpose | Address Block | DNS Zone |
|------|---------|---------------|----------|
| **home** | Production home infrastructure (always-on, stable) | 10.10.0.0/16 | home.deevnet.net |
| **mobile** | Mobile/portable lab for development, testing, and demos | 10.20.0.0/16 | mobile.deevnet.net |

### Builder

The **builder** is a small server that can be connected to either site to create its substrate from scratch. Self-contained, portable, and air-gapped capable, it provisions the site and then hands off authority to production infrastructure. See [Builder](builder/) for the provisioning model, authority transitions, and design principles.

### Substrate

The **substrate** is the shared infrastructure foundation within a site — networking, compute, storage, and management plane. It provides the base that workloads run on and is fully reprovisioned through automation. See [Substrate](substrate/) for infrastructure layers and authority modes.

### Tenant

A **tenant** is an isolated workload boundary for applications and services running on a site's substrate. Each tenant has its own virtual network, its own DNS zone and its own workloads, all created for it by the substrate's control plane when the tenant asks. Creating one changes nothing physical. See [Tenant](tenant/) for tenant networking, lifecycle management, and provisioning.

### Edge Devices

An **edge device** is a physical thing an application owns — a microcontroller, a gateway, a sensor — that the platform attaches to an access network according to how far its firmware is trusted. It is neither substrate nor tenant: the application owns its purpose and its firmware, the platform owns only what it must know to attach and authenticate it. See [Edge Devices](edge-devices/) for the ownership model, and [Access](edge-devices/access/) for how a device reaches the services its application exposes.

### Network Segmentation

The network segmentation model that divides each substrate into isolated broadcast domains, enforcing trust boundaries and traffic separation at the network layer. See [Network Segmentation](network-segmentation/) for segment types, trust hierarchy, default routing policy, and authority mode transitions.

### Naming and Addressing

How each site is addressed, and how hosts and tenant workloads get their addresses and names. See [Naming and Addressing](naming-and-addressing/) for the site address plan, WAN operation modes, the chain from declared identity to address and name, and the two naming authorities.

### Limits

What the hardware underneath the architecture cannot do — no out-of-band management, nothing clustered, local storage, and a single instance of every network device. Deevnet is designed to be rebuilt quickly rather than to stay up through a failure. See [Limits](limits/) for each constraint, what compensates for it, and what lifting it would take.
