---
title: "Management Plane"
weight: 4
aliases:
  - /docs/architecture/substrate/management-plane/core-services/
  - /docs/architecture/substrate/management-plane/extended-services/
  - /docs/architecture/substrate/management-plane/substrate-services/
---

# Management Plane

### Purpose

The management plane is the set of services a substrate runs on its own virtual compute to
**manage and observe itself**: configuring its network devices, and collecting its logs and
metrics. Substrate automation builds these services, and they are rebuilt from code like
everything else in the substrate.

> *What does the substrate run so it can manage itself?*

Its audience is **operators and substrate hosts**. The services the substrate runs for *tenants and
devices* — the provisioning API, tenant names, the secret store, the broker — are a different plane
with a different audience, on different segments: see
[Control Plane](/docs/architecture/substrate/control-plane/). No host belongs to both.


---

## Where It Sits

The plane sits on top of the builder and the core network. It depends on both, and neither
depends on it:

| Layer | Provides | Defined in |
|-------|----------|------------|
| **Builder** | Creates the substrate from nothing, including this plane | [Builder](/docs/architecture/builder/) |
| **Network** | Routing, firewall, name resolution, address reservations, NAT, switching, wireless | [Networking](/docs/architecture/substrate/networking/) |
| **Management Plane** | Services that need compute: network device management and substrate observability | This page |


{{< graphviz >}}
digraph plane {
    graph [
        rankdir=TB,
        nodesep=0.45,
        ranksep=0.55,
        fontname="Helvetica",
        bgcolor="#e0e0e0",
        pad=0.25,
        size="7,9!"
    ]
    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=13, margin="0.25,0.12", penwidth=1.2]
    edge [arrowsize=0.7, fontname="Helvetica", fontsize=11, fontcolor="#333333", color="#555555"]

    builder [label=<<b>Builder</b><br/><font point-size="10">creates everything below from code</font>>, fillcolor="#f6e3c4"]
    network [label=<<b>Core network</b><br/><font point-size="10">routing, zone policy, names, reservations</font>>, fillcolor="#e0f0ff"]

    subgraph cluster_mgmt {
        label=<<b>Management segment: </b>the management plane>
        labeljust=l
        fontname="Helvetica"
        fontsize=11
        style="dashed,rounded,filled"
        fillcolor="#eef3f8"
        color="#6b8aa8"
        margin=14

        nms [label=<<b>Network device management</b><br/><font point-size="10">applies inventory to the switch and APs</font>>, fillcolor="#d0e8d0"]
        obs [label=<<b>Substrate observability</b><br/><font point-size="10">collects logs and metrics</font>>, fillcolor="#d0e8d0"]
        { rank=same; nms; obs }
    }

    devices [label=<<b>Switch, access points</b><br/><font point-size="10">managed on Management</font>>, fillcolor=white]
    cp [label=<<b>Control plane hosts</b><br/><font point-size="10">Platform and IoT Backend</font>>, fillcolor=white]

    builder -> network [label="  builds"]
    builder -> nms [label="  builds"]
    builder -> obs [label="  builds"]
    network -> nms [label="  carries", style=dashed]
    network -> obs [label="  carries", style=dashed]
    nms -> devices [label="  configures"]
    obs -> cp [label="  pulls from", style=dashed]
}
{{< /graphviz >}}

**Every arrow points down: the plane depends on the builder and the network, and nothing below it
depends on the plane.** The collector reaches into Platform and IoT Backend by pulling, so nothing
there ever opens a connection into Management.

This ordering is what keeps a rebuild possible. The core network comes up without the plane, and
the builder can rebuild the plane when every service in it is gone. **The plane helps a rebuild
but is never needed for one.**

The plane's services sit on the **management segment**, alongside the infrastructure they manage.
Operators and substrate hosts use them.

---

## Services and where they sit

| Service | Segment | Why there |
|---|---|---|
| **Network device management**: the controller for the switch and access points | Management | Adopting a device needs the device and the controller on the same segment, and devices are managed on Management |
| **Substrate observability**: logs and metrics about the substrate | Management | Tenants and devices must never reach it |

Automation runners and access tooling belong to this plane too, when they are built. Services are
placed by audience, one segment each, as in the
[control plane](/docs/architecture/substrate/control-plane/#services-and-where-they-sit). How they
are packaged into VMs is [Substrate Service VMs](/docs/platforms/management-plane/substrate-service-vms/).

### Network management

- **Inventory owns network device configuration, and the controller applies it.** The controller
  is the actuator, not the source of truth
  ([ADR-0009](/docs/architecture/decisions/substrate/0009-network-device-config-ownership/)).
- **The controller's database is derived state.** A new controller is a fresh install that inventory
  provisions, not a migration.
- **The pre-VLAN substrate is built without it.** The core router and a standalone access switch
  come first; the controller is needed only once devices are adopted.

### Substrate observability

- **It collects by pull from the Platform and IoT Backend segments**, which the zone policy does not
  let reach Management. Hosts on Management push to it.

---

## How the plane is watched

**Today the only watching is each service's own restart: a failed service restarts every few
seconds, and nobody is told.** No collector runs yet, so nothing measures the plane, and a fault
comes to light when someone next uses the service. Collection and alerting are proposed in
[ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/).

Whatever watches the plane keeps to these rules:

- **The plane is watched by pull, from Management.** Management reaches every zone, so a collector
  there needs no new path into it, and no host on Platform or IoT Backend opens one.
- **A service's health is measured from its own answer, not its host's state.** A VM the hypervisor
  reports as running can still be off the network
  ([INC-0002](/docs/incidents/2026/0002-controller-vm-network-hang/)).
- **The watcher is part of the plane, so it is never needed for recovery.** Losing it loses sight of
  the site, not the ability to rebuild it.
- **A fault has to reach the operator wherever they are.** An alert that can only be read on the
  site's own network is not delivered.

**Who watches the watcher is open.** If the collector or the alert path is down, nothing yet notices.
The [Extended Management Plane plan](/docs/roadmap/infrastructure/substrate/management-plane/plan/)
carries it, with ADR-0023.

---

## Network Identity

Every host in the plane:

- has a **stable, predictable network identity**
- carries a **deterministic layer-2 identity**, defined in version control rather than assigned by
  whatever creates the interface
- receives a **fixed address via reservation**, keyed to that layer-2 identity, rather than an
  address configured into the host itself
- has deterministic DNS records, with services reached by name rather than by host

Addressing by reservation rather than by host configuration is what makes a rebuild
identity-preserving. The host asks for an address and is always given the same one, so nothing
inside the host has to be restored for it to return to the network as itself.

---

## Failure Philosophy

If something breaks:

- Workloads may be destroyed and rebuilt
- The core network keeps routing, resolving and leasing without this plane
- The builder can rebuild any service in the plane from code

A service in the plane can make recovery easier. It must never be required for it.

---

## Architectural Invariants

The management plane is considered **correct** when:

- the core network comes up, and a site can be rebuilt, with every service in the plane gone
- no host has an interface on more than one segment
- services with different audiences never share a host
- services are reached by stable names, so the host behind a name can be replaced without changing
  what consumers reference
- no workload code runs in the plane
- anything in it that is not derived state is backed up

If the substrate must be "mostly working" in order to rebuild the plane, the architecture is
incorrect.
