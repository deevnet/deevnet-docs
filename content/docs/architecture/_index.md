---
title: "Architecture"
weight: 1
bookCollapseSection: true
---

# Architecture

A **substrate** is a self-contained infrastructure environment — its own networking (routing, DNS, DHCP, segmentation), compute, storage, and management plane, all defined as code. Substrates are independent: each one can be built, operated, and torn down without affecting any other. They are also stateless — all configuration lives in source control and is applied through automation, so any substrate can be reprovisioned from scratch at any time.

**Tenants** are logical workload namespaces (application or service domains) that run *on* substrates. A tenant defines what runs; a substrate defines where and how it runs.

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
    Builder [label="Builder"]

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
        MgmtHV [label="Extended\nServices", width=2.2]

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

### [Substrate](substrate/)

The diagram above shows a single substrate. Each substrate is independent — it can be built, operated, and torn down without affecting any other — and stateless, with all configuration defined in source control. The [Substrate Architecture](substrate/) section covers infrastructure layers, networking, management plane, and the builder provisioning model.

### [Tenant](tenant/)

A **tenant** is a logical workload namespace representing an application or service domain.

Examples: `grooveiq`, `vintronics`, `moneyrouter`

Tenants live **on** substrates, not defining them:
- [Networking](tenant/networking/) — Tenant network isolation and VLAN model
- [Management](tenant/management/) — Tenant lifecycle and observability
- [Building](tenant/building/) — Tenant provisioning

---

## Standards

Design principles, correctness invariants, and infrastructure rules are defined in [Standards](/docs/standards/):

- [Correctness](/docs/standards/correctness/) — What it means for infrastructure to be correct
- [Identity vs Intent](/docs/standards/identity-vs-intent/) — Separation of host identity from workload intent
- [Naming](/docs/standards/naming/) — How systems and services are named
