---
title: "CHG-0012: Operator Access to Tenant Workloads"
weight: 12
---

# CHG-0012: Operator Access to Tenant Workloads

| | |
|---|---|
| **Date** | 2026-09-18 |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | 2026-09-18 |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` (core router, static route and zone policy); `ansible-inventory-deevnet` firewall policy |
| **Automation** | The route is applied by hand — no role manages OPNsense static routes. The zone-policy rules are inventory, applied by `deevnet.net` `opnsense_firewall` when [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) runs. |
| **Risk** | Low — it adds reachability and removes none. The one thing most likely to go wrong is the route being written to the wrong gateway, which fails closed. |
| **Related changes** | [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/), which must not undo it |
| **Related incidents** | None |
| **Related runbooks** | None |

---

## Summary

A tenant workload cannot be reached from anywhere today. Building, checking or debugging one means
the hypervisor console, or `ip vrf exec` from the exit node as root — the most privileged access the
substrate has, used for ordinary work.

This adds **one aggregate route** on the core router, `10.20.128.0/18` via the fabric exit node
`10.20.50.22`, and declares the zone-policy rules that let `management` and `trusted` use it. After
it, an operator on the Builder or on a desktop can reach any tenant workload directly.

[ADR-0018](/docs/architecture/decisions/0018-operator-access-to-tenants/) is the decision; it
records what this does to the "no inbound path" property and what it deliberately does not
authorise.

### Why one route covers every tenant

ADR-0002 allocates the tenant overlay as a `/18` — subnet `10.20.(128+index).0/24`, indexes 1 to 62
with 63 reserved. A single `10.20.128.0/18` therefore covers every tenant that can ever exist at
this site, so adding a tenant still requires no substrate change.

### What is already in place

Verified before planning, so the change is genuinely one route:

- The exit node already forwards into every tenant VRF — FRR leaks each tenant subnet into its
  default table (`proto bgp`).
- SNAT does not interfere. It matches `-s <tenant> -o vmbr0.50`, and the `nat` table is consulted
  only for a connection's first packet, so replies to an inbound-initiated session are not
  translated. A TCP connection to a workload's port 22 from inside the VRF succeeded.
- The credential already exists: a workload's `a_autoprov` account trusts the substrate's automation
  key, baked into the base image with passwordless sudo.

### Why the route must be on the router, not on a host

A route added on the Builder alone was tested first. **ICMP worked and TCP timed out**: the SYN went
Builder → exit node via management, but the reply returned via the core router, which dropped a
SYN-ACK whose SYN it had never seen. Routing at the core router makes both legs symmetric, which is
what TCP needs.

## Goal

- `ssh a_autoprov@<workload address>` succeeds from the Builder (management).
- The same succeeds from a desktop on trusted, 10.20.10.0/24.
- A tenant's egress is unchanged: it still reaches platform, IoT backend and the internet.
- `iot`, `iot_vendor` and `guest` still cannot reach a tenant workload.
- The zone policy names `10.20.128.0/18` explicitly, so CHG-0007 will preserve this access.

## Scope

**In scope:** one static route on the core router; two zone-policy rules in inventory.

**Out of scope:** applying the zone policy (that is CHG-0007); bringing the route under automation;
replacing the shared `a_autoprov` key; any change to tenant egress or to what devices may reach.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Route points at the wrong gateway | core router | It fails closed — no reachability gained, nothing else affected. Verified by the goal tests before the change is called done. |
| The new rules widen access further than intended | inventory | Both rules name `10.20.128.0/18` as the destination and `management` / `trusted` as the source. No other zone is touched, and the reverse direction is not added. |
| CHG-0007 later removes the access | core router | The rules are declared in inventory now, so CHG-0007 renders them. This is the whole reason they are written before they are needed. |
| Tenant egress disturbed | exit node | Nothing on the exit node changes. Egress is re-tested after the route is added. |
| The route is lost in a router rebuild | core router | **Not guarded.** No role manages it. Recorded as the first follow-up. |

## Prerequisites

- [ ] [ADR-0018](/docs/architecture/decisions/0018-operator-access-to-tenants/) reviewed — this
      changes a property six records rely on
- [ ] A tenant workload running, to test against
- [ ] Console access to the core router, in case a routing change misbehaves

## Procedure

### Step 1: Add the static route

Not disruptive: it adds a route where none existed.

**Run:** on `dv02cor002p01`, System → Routes → Configuration, add:

| Field | Value |
|---|---|
| Network address | `10.20.128.0/18` |
| Gateway | the fabric exit node on transit, `10.20.50.22` |
| Description | `CHG-0012: tenant overlay via fabric exit node (ADR-0018)` |

**Verify:**

1. The route appears in System → Routes → Status.
2. From the Builder: `ping 10.20.130.10` answers.
3. From the Builder: `ssh a_autoprov@10.20.130.10` reaches a shell.
4. From a desktop on 10.20.10.0/24: the same.

**Undo:** [Undo Step 1](#undo-step-1)

### Step 2: Declare the zone-policy rules

Inventory only. Nothing is applied to the router by this step — the router passes everything until
CHG-0007 runs, and these rules are what make CHG-0007 preserve the access rather than remove it.

**Run:** in `ansible-inventory-deevnet`, add to `firewall_zone_policies`:

```yaml
- { from_zone: management, to_zone: tenant_transit, destination_net: "10.20.128.0/18",
    name: "tenant overlay (ADR-0018)" }
- { from_zone: trusted, to_zone: tenant_transit, destination_net: "10.20.128.0/18",
    name: "tenant overlay (ADR-0018)" }
```

The `destination_net` override is required. The existing `-> tenant_transit` rules render
`10.20.50.0/24` from the zone's own subnet, which is the transit segment and not the tenant overlay.

**Verify:**

1. `--check --diff` against the core router shows exactly two added rules, both with destination
   `10.20.128.0/18`, and no other rule changed.

**Undo:** [Undo Step 2](#undo-step-2)

## Verification

An operator reaches a tenant workload from both management and trusted, by name and by address. A
tenant's egress is unchanged. No zone other than management and trusted gains a path, confirmed by
reading the rendered rule set rather than by inference.

## Undo

Reverse order. There is no point of no return: the route is one row, and the rules are inventory
that has not been applied.

### Undo Step 1

Delete the route. Reachability returns to what it was; nothing else depends on it.

### Undo Step 2

Revert the inventory commit. Nothing was applied, so nothing on the router changes.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] **The route is unmanaged and will be lost in a router rebuild**, silently, because nothing
      tests it. No role manages OPNsense static routes. Either the `deevnet.net` collection gains
      route management, or the rebuild runbook carries this route explicitly — the first is right,
      the second is the minimum.
- [ ] **Every tenant workload trusts the substrate's automation key.** The kickstart bakes
      `a_autoprov_rsa.pub` into the base image with passwordless sudo, so one key reaches root on
      every tenant workload. It was unreachable before this change and is not now. The end state is
      a per-tenant or per-operator key; deferred deliberately, and recorded so the deferral is
      visible.
- [ ] **The SNAT rules on the exit node are duplicated** — `10.20.129.0/24` appears four times and
      `10.20.130.0/24` twice. Functionally harmless, but the insertion is not idempotent and the
      list grows on every run.
- [ ] Operator access to a tenant workload leaves no audit trail
      ([ADR-0018](/docs/architecture/decisions/0018-operator-access-to-tenants/) open question 2).
