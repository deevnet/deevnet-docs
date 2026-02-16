---
title: "Architecture"
weight: 1
bookCollapseSection: true
---

# Architecture

Deevnet architecture is organized around **substrates** (independent infrastructure environments) and **tenants** (logical workload namespaces that run on substrates).

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
        pad=0.15
    ]
    node [shape=box, style="rounded,filled", fillcolor=white, fontname="Helvetica"]
    edge [arrowsize=0.7, fontname="Helvetica"]

    // Top row - force same rank for Edge Router and Builder
    Internet [label="Internet/Upstream LAN", width=2.5]
    EdgeRouter [label="Edge Router"]
    Builder [label="Builder Node"]

    Internet -> EdgeRouter
    { rank=same; EdgeRouter; Builder }
    EdgeRouter -> Builder [minlen=2]

    subgraph cluster_substrate {
        label="Substrate"
        style=filled
        fillcolor="#e0f0ff"

        CoreRouter [label="Core Router\nDNS, DHCP, Firewall", width=2.5]
        WirelessAP [label="Wireless AP", width=1.0]
        AccessSwitch [label="Access Switch", width=4.5]
        MgmtHV [label="Management Plane\nHypervisor", width=2.2]

        subgraph cluster_tenant {
            label="Tenant"
            style=filled
            fillcolor="#fff3cd"

            TenantHV [label="Tenant\nHypervisor"]
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

### [Substrate](substrate/)

A **substrate** is an infrastructure environment—a self-contained network with its own compute, storage, and management plane.

- **dvntm** — Mobile/portable lab for development, testing, and demos
- **dvnt** — Production home infrastructure (always-on, stable)

#### Substrate Independence

Each substrate operates independently through its **networking** and **management plane**:

- **Networking** — Self-contained routing, DNS, DHCP, and segmentation via Core Router
- **Management Plane** — Provisioning, observability, and operational services

{{< hint info >}}
No cross-substrate dependencies for core functionality. Each substrate can be built, operated, and torn down without affecting the other.
{{< /hint >}}

#### Stateless Infrastructure

{{< hint info >}}
Substrate infrastructure is **stateless**. All configuration is defined in source control and applied via Ansible — no backup, restore, or data recovery required for the substrate itself.
{{< /hint >}}

Benefits:
- **Rebuild from scratch** — Any host can be wiped and reprovisioned
- **Hardware replacement** — Swap failed hardware without data migration
- **No snapshots or backups** — Configuration is code, not state

Tenant workloads may have stateful data requiring separate backup/recovery procedures.

#### What a Substrate Provides

A substrate provides virtualization services and compute resources for tenant workloads. For **dvntm** specifically, it serves as a stable, portable network that remains insulated from upstream internet connectivity—whether connected to home, hotel, or conference WiFi, the internal network remains consistent.

See:
- [Networking](substrate/networking/) — Network segmentation and VLAN model
- [Management Plane](substrate/management-plane/) — Infrastructure management, DNS authority, and VM-based services

#### Builder (Bootstrap Node)

The **builder** is architecturally part of the substrate but operates with independence—it can move between substrates and provision whichever environment it's connected to. The builder contains all artifacts and automation needed for air-gapped substrate provisioning.

See [Builder](substrate/builder/) for the bootstrap node and provisioning architecture.

### [Tenant](tenant/)

A **tenant** is a logical workload namespace representing an application or service domain.

Examples: `grooveiq`, `vintronics`, `moneyrouter`

Tenants live **on** substrates, not defining them:
- [Networking](tenant/networking/) — Tenant network isolation and VLAN model
- [Management](tenant/management/) — Tenant lifecycle and observability
- [Building](tenant/building/) — Tenant provisioning with Terraform

---

## Standards

Design principles, correctness invariants, and infrastructure rules are defined in [Standards](/docs/standards/):

- [Correctness](/docs/standards/correctness/) — What it means for infrastructure to be correct
- [Identity vs Intent](/docs/standards/identity-vs-intent/) — Separation of host identity from workload intent
- [Naming](/docs/standards/naming/) — How systems and services are named
