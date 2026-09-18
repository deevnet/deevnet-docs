---
title: "ADR-0018: Operator Access to Tenant Workloads"
weight: 18
---

# ADR-0018: Operator Access to Tenant Workloads

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-18 |
| **Scope** | Whether the substrate's operator networks may reach tenant workloads, and what that does to the "no inbound path" property other records rely on |
| **Supersedes, in part** | [ADR-0001: Tenant Network Fabric](/docs/architecture/decisions/0001-tenant-network-fabric/) and [ADR-0002: Tenant Fabric Numbering](/docs/architecture/decisions/0002-tenant-fabric-numbering/), where each says the core router **never learns tenant address space**. It now learns one aggregate route. Everything else in both records stands, including SNAT at the exit node and per-tenant isolation inside the fabric. |
| **Related** | [ADR-0003: Tenant Egress on a Single-Member Fabric](/docs/architecture/decisions/0003-tenant-egress-single-member-fabric/), [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/), [ADR-0011: Edge Devices Are Application-Owned](/docs/architecture/decisions/0011-edge-devices-application-owned/), [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/), [ADR-0017: How Tenant Code Reaches a Tenant Workload](/docs/architecture/decisions/0017-tenant-code-delivery/) |

---

## Context

### The property, and who relies on it

Six records state some form of "a tenant has no inbound path". They do not all mean the same thing,
and the difference matters:

| Claim | Where | After this decision |
|---|---|---|
| The core router never learns tenant address space | ADR-0001, ADR-0002, tenant networking page | **False.** It learns one `/18`. |
| A device on IoT cannot reach a tenant | ADR-0011, ADR-0012, shared services page | **Still true.** No zone rule permits it, and none is proposed. |
| One tenant cannot reach another | ADR-0001, enforced by VRF | **Still true.** Enforced inside the fabric, untouched here. |
| Nothing outside the substrate can reach a tenant | ADR-0003 | **Still true.** The perimeter is unchanged. |

So what changes is narrow: **the substrate's own operator networks gain a route to tenant
workloads.** Everything the property was invoked to protect — devices, tenant isolation, the
perimeter — is unaffected.

### Why it is wanted

The operator owns every tenant on this substrate. Building a tenant, checking one, and debugging one
are all things done from the Builder or from a desktop on the trusted network, and today none of
them is possible: a tenant workload cannot be reached at all, so the only way in is the hypervisor
console or `ip vrf exec` from the exit node as root.

That is a poor tool for ordinary work, and it pushes every investigation through the most privileged
access the substrate has.

### It is an overlap, not the removal of a boundary

The AWS analogy in [ADR-0010](/docs/architecture/decisions/0010-tenants-consume-platform-services/)
says a provider does not reach into a customer's instances. That analogy holds where it earns its
keep — tenants own their code, their devices and their secrets — and it stops being useful when it
creates real inconvenience for an operator who is also every tenant.

The operator's own framing: the logical boundaries remain; this is an overlap between roles held by
the same person, not the erasure of the distinction. A later site with tenants owned by someone else
would not get this route, and nothing here assumes it.

### What was measured

Checked on 2026-09-18, before deciding:

- **The fabric already leaks every tenant subnet into the exit node's default table** — FRR installs
  `10.20.129.0/24 dev vrf_tdemo` and `10.20.130.0/24 dev vrf_eds`, `proto bgp`. The exit node can
  already forward into any tenant VRF; nothing new is needed there.
- **FRR does not peer with the core router** (`No BGP neighbors found`), so the route is static.
- **SNAT does not interfere.** The rule matches `-s <tenant> -o vmbr0.50`, and the `nat` table is
  consulted only for a connection's first packet, so replies to an inbound-initiated session are
  never translated. Confirmed by a TCP connection to a workload's port 22 from inside the VRF.
- **Asymmetric routing fails, and that is what forces the route onto the router.** A route added on
  the Builder alone made ICMP work and TCP time out: the SYN went via management, the SYN-ACK
  returned via the core router, and the router dropped a reply whose SYN it never saw. Routing at
  the core router makes both legs symmetric.
- **A workload's `a_autoprov` account already trusts the substrate's automation key**, baked into
  the base image by the kickstart along with passwordless sudo. The credential side of this access
  already exists; only the route was missing.

---

## Decision

**The core router carries one aggregate route to the tenant overlay**, `10.20.128.0/18` via the
fabric exit node, and the zone policy permits `management` and `trusted` to reach it.

- **One route, not one per tenant.** ADR-0002 allocates the overlay as a `/18`, so a single route
  covers all 63 indexes and adding a tenant still requires no substrate change.
- **Two source zones only.** `management` and `trusted`. No other zone gains a path, and in
  particular `iot`, `iot_vendor` and `guest` do not.
- **The direction is one-way.** This is the operator reaching a tenant. It does not give a tenant a
  path to management or trusted, and the existing egress rules are unchanged.
- **The `/18` must be named explicitly in the zone policy.** The existing
  `trusted -> tenant_transit` and `management -> tenant_transit` rules permit `10.20.50.0/24`, the
  transit segment, because rules are rendered from each zone's subnet. The tenant overlay is a
  different address space and is not covered by them.

### What this does not authorise

**It is not a delivery mechanism for tenant code.** [ADR-0017](/docs/architecture/decisions/0017-tenant-code-delivery/)
holds: tenant application code is pulled by the workload, not pushed by the substrate. The
difference is between *operating* a machine — reaching it to look, to debug, to run a check — and
*owning what runs on it*, which stays with the tenant.

That line matters because it is the one that erodes quietly. Ansible from the Builder can now reach
a tenant workload, and the temptation to deploy tenant applications that way will be real and will
look reasonable each time. The boundary is now a decision rather than a physical fact, and a
decision has to be kept.

---

## Consequences

- **"A tenant has no inbound path" is no longer true as stated** and must be qualified wherever it
  appears: no inbound path *from devices, from other tenants, or from outside the substrate*.
- **The core router now holds tenant-specific configuration** — the thing ADR-0001 avoided. It is
  one aggregate route rather than per-tenant state, which keeps the property that mattered.
- **The route is unmanaged.** No role manages OPNsense static routes, so this one is applied by hand
  and will be lost in a router rebuild — silently, because nothing tests it. That is a follow-up on
  [CHG-0012](/docs/changes/2026/0012-operator-access-to-tenants/), not an acceptable end state.
- **The blast radius of the shared `a_autoprov` key grows.** It was already baked into every tenant
  workload with passwordless sudo; it was simply unreachable. Now that the path exists, one key
  compromise reaches every tenant workload directly. This is recorded as a defect, not accepted as a
  design.
- **A tenant cannot tell.** Nothing in the tenant-facing contract changes, and a tenant has no way
  to observe or refuse the access.

---

## Open questions

1. **Should the route be conditional on the site?** A future site whose tenants are not the
   operator's should not carry it. Nothing today distinguishes those cases.
2. **Does operator access need an audit trail?** Reaching a tenant workload leaves no record on the
   substrate. For a single-owner lab that is tolerable; for the model this substrate is imitating it
   is not.
3. **Should tenant workloads stop trusting the substrate's automation key?** The correct end state
   is a per-tenant or per-operator key that a tenant could in principle rotate. Deferred
   deliberately; see the CHG-0012 follow-up.

---

## Current state

Proposed. Nothing is applied. [CHG-0012](/docs/changes/2026/0012-operator-access-to-tenants/) is the
change that applies it.
