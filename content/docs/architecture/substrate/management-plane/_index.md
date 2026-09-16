---
title: "Management / Control Plane"
weight: 4
bookCollapseSection: true
aliases:
  - /docs/architecture/substrate/management-plane/core-services/
  - /docs/architecture/substrate/management-plane/extended-services/
---

# Management / Control Plane

### Purpose

The management / control plane is the set of services a substrate runs on its own virtual compute.
The services are there for **two audiences**:

- **The substrate itself**: managing network devices and observing the substrate
- **Tenants and their devices**: the services a tenant consumes instead of running its own

Both kinds of service belong to the substrate. Substrate automation builds them, they are rebuilt
from code like everything else in the substrate, and no tenant code runs on them.

> *What does the substrate run so it can manage itself, and so tenants don't each have to?*

---

## Where It Sits

The plane sits on top of the builder and the core network. It depends on both, and neither
depends on it:

| Layer | Provides | Defined in |
|-------|----------|------------|
| **Builder** | Creates the substrate from nothing, including this plane | [Builder](/docs/architecture/builder/) |
| **Network** | Routing, firewall, name resolution, address reservations, NAT, switching, wireless | [Networking](/docs/architecture/substrate/networking/) |
| **Management / Control Plane** | Services that need compute: device management, observability, and the services tenants consume | This section |

This ordering is what keeps a rebuild possible. The core network comes up without the plane, and
the builder can rebuild the plane when every service in it is gone. **The plane helps a rebuild
but is never needed for one.**

---

## Two Kinds of Service

{{< graphviz >}}
digraph control_plane {
    graph [
        rankdir=TB,
        splines=ortho,
        nodesep=0.5,
        ranksep=1.0,
        fontname="Helvetica",
        bgcolor="#e0e0e0",
        pad=0.15,
        size="6.5,8"
    ]
    node [shape=box, style="rounded,filled", fillcolor=white, fontname="Helvetica", fontsize=11]
    edge [arrowsize=0.7, fontname="Helvetica", fontsize=10, minlen=2]

    Operators [label="Operators and\nsubstrate hosts"]
    Tenants [label="Tenants"]
    Devices [label="Edge / IoT\ndevices"]

    subgraph cluster_plane {
        label="Management / Control Plane"
        style=filled
        fillcolor="#fff3cd"

        subgraph cluster_substrate_svc {
            label="Substrate Services\n(management segment)"
            labelloc=b
            style=filled
            fillcolor="#e0f0ff"

            NetMgmt [label="Network\nmanagement"]
            SubObs [label="Substrate\nobservability"]
        }

        subgraph cluster_tenant_svc {
            label="Shared Tenant Services\n(platform and IoT backend segments)"
            labelloc=b
            style=filled
            fillcolor="#d0e8d0"

            Prov [label="Provisioning"]
            Ident [label="Identity"]
            TenObs [label="Tenant\nobservability"]
            Msg [label="Device\nmessaging"]
        }
    }

    Operators -> NetMgmt
    Operators -> SubObs
    Tenants -> Prov
    Tenants -> Ident
    Tenants -> TenObs
    Devices -> Msg
}
{{< /graphviz >}}

| | Substrate Services | Shared Tenant Services |
|---|---|---|
| **Serves** | The substrate itself | Tenants, and the devices tenants own |
| **Segment** | Management | Platform, and IoT backend for device messaging |
| **Reached by** | Operators and substrate hosts | Tenants over the tenant perimeter, and devices on the IoT segment |
| **Change cadence** | Frequent (observability is changed often) | Slow and deliberate, because tenants depend on it |
| **Detail** | [Substrate Services](substrate-services/) | [Shared Tenant Services](shared-tenant-services/) |

The split follows the network segmentation standard as well as the audience:

- **Tenants must not reach the management segment.** A service tenants use therefore can't sit
  there, even though the substrate owns it.
- **Substrate-facing and tenant-facing services have different change cadences.** Keeping them on
  separate hosts means a restart in the frequently changed tier can't take tenant name resolution
  with it ([ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/)).

---

## Domains

Services are grouped into **domains** by what they are for, not by which segment they sit on or
what kind of software they are
([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/)):

| Domain | Kind | Holds |
|--------|------|-------|
| **Network management** | Substrate | The controller that applies network device configuration from inventory; later, network monitoring and config backup |
| **Substrate observability** | Substrate | Logs and metrics about the substrate |
| **Provisioning** | Shared tenant | What a tenant's infrastructure code talks to: the platform API and the state store |
| **Identity** | Shared tenant | Tenant authoritative DNS; later, a directory |
| **Tenant observability** | Shared tenant | Logs and metrics tenants share |
| **Device messaging** | Shared tenant | The message broker devices connect to, and its authentication store |

How domains map onto hosts:

- **Each domain is one host, on exactly one segment.** Anything that crosses segments goes through
  the core router and its zone policy, so no host quietly bridges two zones.
- **A domain that needs two segments becomes two domains.** Observability is the first case: one
  domain for the substrate on management, and one for tenants on platform.
- **Each service inside a domain stays separable.** It runs in its own container, with its own data
  and its own inventory group. Moving a service to another host is a change to inventory, not a
  redesign.
- **A new service joins the domain it belongs to.** If no domain fits, it becomes a new domain.
- **Services in one domain share the host's fate.** Rebooting a host takes all of its services
  with it. That is accepted at lab scale, and it is why the two audiences never share a host.

---

## How Tenants Consume the Plane

The rule that governs every shared tenant service
([ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/), *Proposed*):

> **A tenant may depend on the substrate; the substrate must not come to contain the tenant.**

What makes a substrate-run service safe for tenants to depend on:

1. **The substrate runs it**, as substrate code applied by substrate automation.
2. **A tenant is bound to it once, at onboarding**, when the substrate issues a credential, a
   namespace or both.
3. **The tenant then uses it through the service's own interface.** No recurring tenant action
   needs a change to the substrate.
4. **The service confines each tenant to its own scope.** Where the backing software can't do
   that, the service isn't offered as self-service until something in front of it can.
5. **Whatever a tenant puts into it can be rebuilt from the tenant's own code.** The substrate may
   host that content, but it never holds the only copy.

The test for any proposed service:

> **Does this recurring tenant action need a substrate commit?** Onboarding may. Nothing that
> recurs may.

---

## The Server Is Substrate; the Content Is Tenant

The plane is provisioned by **substrate automation**, run from the builder. Tenant infrastructure
tooling never provisions it, even where a service exists only to serve tenants.

| | Owner | Written by |
|---|---|---|
| The host, the service, and its configuration | Substrate | Substrate automation |
| A tenant's zone, credential or namespace | Substrate, at onboarding | Substrate automation |
| What goes inside it (records, state, device registrations) | Tenant | The tenant's own infrastructure code |

This prevents a bootstrap cycle. The state store tenants keep their state in is built by
automation that keeps no state in it. If the plane were built by the tooling that uses the store,
the store's own state would have nowhere to live
([ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/)).

---

## Network Identity

Every host in the plane, substrate-facing and tenant-facing alike:

- Have **stable, predictable network identities**
- Carry a **deterministic layer-2 identity**, defined in version control rather than assigned by
  whatever creates the interface
- Receive **fixed addresses via reservation**, keyed to that layer-2 identity, rather than
  addresses configured into the host itself
- Have deterministic DNS records, with services reached by name rather than by host

Addressing by reservation rather than by host configuration is what makes a rebuild
identity-preserving. The host asks for an address and is always given the same one, so nothing
inside the host has to be restored for it to return to the network as itself.

---

## Architectural Invariants

The management / control plane is considered **correct** when:

- the core network comes up, and a site can be rebuilt, with every service in the plane gone
- substrate services and shared tenant services never share a host
- no host has an interface on more than one segment
- no tenant can reach the management segment to use a service
- no recurring tenant action needs a substrate commit
- tenant content held in a shared service is never the only copy
- services are reached by stable names, so the host behind a name can be replaced without changing
  what consumers reference
- no tenant code runs in the plane

If rebuilding the plane loses something a tenant can't restore from its own code, the architecture
is incorrect.
