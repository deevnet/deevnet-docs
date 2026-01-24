---
title: "Architecture"
weight: 1
bookCollapseSection: true
---

# Architecture

Deevnet architecture is organized around **substrates** (independent infrastructure environments) and **tenants** (logical workload namespaces that run on substrates).

---

## Substrate Architecture

{{< mermaid >}}
flowchart TB
    Internet[Internet]
    Internet --> EdgeRouter[Edge Router]
    EdgeRouter --- Builder[Builder Node]

    subgraph Substrate[" Substrate"]
        CoreRouter[Core Router<br>DNS, DHCP, Firewall]
        WirelessAP[Wireless AP]
        AccessSwitch[Access Switch]
        MgmtHV[Management<br>Hypervisor]

        subgraph Tenant[" Tenant"]
            TenantHV[Tenant<br>Hypervisor]
            PiCompute[Pi Compute<br>edge/IoT]
        end

        CoreRouter --> WirelessAP
        CoreRouter --> AccessSwitch
        AccessSwitch --> MgmtHV
        AccessSwitch --> TenantHV
        AccessSwitch --> PiCompute
    end

    EdgeRouter --> CoreRouter
    Builder --> AccessSwitch

    style Substrate fill:#e0f0ff,stroke:#333
    style Tenant fill:#fff3cd,stroke:#333
{{< /mermaid >}}

### [Substrate](substrate/)

A **substrate** is an infrastructure environment—a self-contained network with its own compute, storage, and management plane.

- **dvntm** — Mobile/portable lab for development, testing, and demos
- **dvnt** — Production home infrastructure (always-on, stable)

#### Substrate Independence

Each substrate operates independently through its **networking** and **management plane**:

- **Networking** — Self-contained routing, DNS, DHCP, and segmentation via Core Router
- **Management Plane** — Provisioning, observability, and operational services

No cross-substrate dependencies for core functionality. Each substrate can be built, operated, and torn down without affecting the other.

#### Stateless Infrastructure

Substrate infrastructure is **stateless**. All configuration is defined in source control and applied via Ansible—no backup, restore, or data recovery required for the substrate itself.

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
