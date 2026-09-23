---
title: "ADR-0027: Tenant Log Store"
weight: 27
---

# ADR-0027: The Log Store Is for Tenants Only, and Device Logs Arrive Over MQTT

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-22 |
| **Scope** | Who the central log store is for, what writes into each tenant's partitions, how edge devices' logs reach it over MQTT, and what would justify moving it. |
| **Supersedes, in part** | [ADR-0022: Central Logging](/docs/architecture/decisions/0022-central-logging/). Its **scope**, which included substrate logs, and its §5 shipping of substrate hosts and network devices, including the syslog listener, are replaced. ADR-0022's store, proxy, partition scheme, tokens and "publish, don't filter" rule stand. |
| **Related** | [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/) §8, §10, [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/), [ADR-0018: Operator Access to Tenant Workloads](/docs/architecture/decisions/0018-operator-access-to-tenants/), [CHG-0018: The Central Log Store](/docs/changes/2026/0018-central-log-store/), [INC-0004](/docs/incidents/2026/0004-core-router-lost/) |

---

## Context

### What exists

[CHG-0018](/docs/changes/2026/0018-central-log-store/) built ADR-0022's store on `dv02obs001v01`, a
Platform VM on the management hypervisor: VictoriaLogs behind vmauth, with tenants partitioned by
index. It was verified, and it was completed with nothing shipping to it. ADR-0022 stayed Proposed
until a real writer exists.

### What changed

On 2026-09-22 the operator narrowed what the store is for:
- **The substrate's own logs are not wanted centrally.** CHG-0018 had already withdrawn substrate
  shipping, and this makes the withdrawal permanent.
- **The store is for tenants:**
  - **tenant backend services**, the workloads on the tenant hypervisor
  - **edge devices** that report log messages over MQTT

Two things prompted it:
- The substrate half carried most of ADR-0022's risk:
  - an unauthenticated syslog listener
  - a token on every substrate host
  - SELinux and journal-upload work on each of them
  - substrate command lines at risk of reaching a store that tenants can reach
- [INC-0004](/docs/incidents/2026/0004-core-router-lost/) showed the cost of extra traffic across the
  core router's LAN NIC, which carries every VLAN.

### Where tenant logs actually travel

Checked on `dv02hyp002p02`, 2026-09-22:
- Each tenant is its own EVPN zone and VRF (`vrf_eds`, `vrf_tdemo`), with `snat` on its subnet. The
  tenant hypervisor is the only exit node.
- A workload's line to the store goes: tenant VRF → exit node, SNAT to `10.20.50.22` → tenant_transit →
  the core router → Platform → the management hypervisor. **It crosses the core router's `re0` twice.**
- Devices already reach the broker on `dv02msg001v01` (IoT Backend) through the core router.

---

## Options considered

### Where the store lives

#### A — Stay on `dv02obs001v01` *(chosen, for now)*

- **For:** built and verified; ADR-0023's metrics store and ADR-0024's Grafana are planned beside it;
  location doesn't matter to device logs, which cross the router to reach the broker anyway.
- **Against:** every tenant log line crosses `re0` twice.

#### B — Move to the tenant hypervisor, reachable without the router

A store VM on `dv02hyp002p02`, on-link to the exit node's default VRF: either on tenant_transit or on
a bridge local to that host. Tenant traffic would never leave the host.

- **For:**
  - tenant log traffic stays off `re0` entirely
  - tenant data stays on tenant hardware
  - the store fate-shares with the workloads it serves
- **Against:**
  - Tenant_transit is declared "fabric exit nodes only", and ADR-0013 places substrate services on the
    management hypervisor. Both would need amending.
  - It is local to one tenant hypervisor only; a second would route to it.
  - Device logs don't benefit.
- **Verdict:** Deferred. Consider it only when the evidence in *What would reopen this* holds.

#### C — Move to the tenant hypervisor, on Platform

- **Against:** it moves the VM but not the traffic, which still routes through `re0`.
- **Verdict:** Rejected.

### How device logs arrive

#### A — A substrate bridge, by topic *(chosen)*

One platform service subscribes to the log topic under every tenant's prefix and writes each message
to that tenant's partition.

- **For:**
  - **The tenant is known reliably.** The broker enforces each account's prefix (ADR-0012 §10), so a
    message under `eds/...` was published by an `eds` account. That is exactly what ADR-0022's open
    question 3 said a collector reading third-party logs could not have.
  - Tenants only publish; none has to build a forwarder.
- **Against:** one substrate account can read every tenant's device logs. That is accepted; see
  Consequences.

#### B — Each tenant's backend forwards its own devices' logs

- **Against:** every tenant builds and runs the same forwarder, and a tenant without a backend gets
  no device logs.
- **Verdict:** Not chosen, but not prevented: a tenant may still ship device logs through its own
  workload into `(index, 0)`.

---

## Decision

### 1. The store is for tenants only

- **No substrate host, service or network device ships to the store.** The syslog listener, its source
  list and the per-host substrate ingest tokens are removed (the follow-up change).
- **The substrate still writes about tenants.** ADR-0022 §4 stands: the Deevnet API writes each tenant
  event to that tenant's `(index, 1)`. Only the API writes there.
- **The operator's read token stays.** The operator reads any partition, one at a time (ADR-0022,
  Q1).
- **Off-box logging for the core router is not provided**, by the operator's decision on 2026-09-22.
  INC-0004 relies on crash dumps and the console instead.

### 2. Partitions

| AccountID | ProjectID | Holds | Written by | Read by |
|---|---|---|---|---|
| *tenant index* | `0` | what the tenant's workloads ship | the tenant's ingest token | the tenant, operator |
| *tenant index* | `1` | substrate events about the tenant | the Deevnet API only | the tenant, operator |
| *tenant index* | `2` | **its devices' logs, from MQTT** | the bridge only | the tenant, operator |

- `(0, 0)` no longer has a substrate writer. It holds only CHG-0018's trial and verification lines.
- A tenant's read token covers `(index, 0)`, `(index, 1)` and `(index, 2)`, through vmauth `url_map`
  as ADR-0022 §3 describes. The routing between partitions is built with the tenant tokens.
- **No tenant token can write `(index, 1)` or `(index, 2)`.** What a tenant reads there came from
  the substrate or from its own devices by way of the broker. It is never something a workload wrote
  about itself.

### 3. The log topic

**A new convention, decided here:** a device publishes its log messages under the literal level
`log`, immediately after the tenant prefix:

```
<tenant>/log/<device>
```

- The tenant declares it like any other pattern. For example, eds grants a device account the publish
  pattern `log/lp-stand-01`, and the API stores `eds/log/lp-stand-01` (ADR-0012 §10).
- `log` becomes a **reserved first level** in every tenant's namespace. The API refuses any other use of
  it, for example a subscribe grant on `log/#` to a device account.
- The tenant's workloads may subscribe to their own `log/#`, and that grants nothing across tenants.

**The payload** is either a UTF-8 text line, stored as the message, or a JSON object, stored as
fields with `_msg` if it has one. The bridge adds:
- `tenant` (the name), `device` (the last topic level), and the broker's receive time if the message
  has none
- nothing the device could set to claim another tenant: the partition comes from the topic, never
  from the payload

### 4. The bridge

- **It runs beside the broker, on `dv02msg001v01`**, as a container in the pattern ADR-0013 set.
  - It subscribes on the broker's local listener.
  - It writes to vmauth on `dv02obs001v01` over `iot_backend -> platform`, which is **already
    declared**. Running it beside the store instead would need a new `platform -> iot_backend` rule.
- **Its broker account may subscribe to `+/log/#` and nothing else.**
  - It is provisioned by the substrate, like the broker's own database roles, and not through the API:
    it is not a tenant's account.
  - It may not publish.
- **Its store credential writes only `(index, 2)` partitions.** The mechanism is open (Open question 1).
- **It keeps no state.** A bridge outage loses device logs sent during it, unless they were published
  with QoS 1 and a persistent session, which the bridge uses (Open question 2).
- **It is a small service written for this**, in its own repository
  ([deevnet-log-bridge](https://github.com/deevnet/deevnet-log-bridge)), building its own image as
  the provisioning API does, and deployed in the pattern ADR-0013 set.

  *Corrected 2026-09-22:* an earlier draft of this record said the container image factory would
  build it. That factory is chartered for **third-party** software - "source we may use, binaries we
  may not" - and its version file holds upstream's version, so software we write does not fit it.

  An off-the-shelf collector was considered and not chosen: routing each message to its tenant's
  partition means setting a per-message header, which their HTTP sinks do not express.

### 5. Where the store lives

`dv02obs001v01` for now (Option A). Moving it is reconsidered on evidence, not by default. See *What
would reopen this*.

---

## Consequences

**The store's attack surface shrinks.**
- The unauthenticated syslog path goes.
- Six substrate tokens and the host-side shipping machinery go.
- No substrate command line can reach a store tenants can reach.

**One substrate account reads every tenant's device logs.** The bridge must, to route them. It is a
subscribe-only account on one topic level, held in the vault, and it runs beside the broker, which can
read every message anyway. This is no new exposure in kind: the broker already sees all device
traffic.

**A device's log is only as trustworthy as its account.** The partition is right, because the broker
enforces the prefix. The content is whatever the device sent. A compromised device can fill its own
tenant's `(index, 2)`, never another tenant's.

**Device logs share `re0` with everything else.** Device → broker crosses the core router today, and
bridge → store crosses it again. Location doesn't change that; the NIC fix does.

**The core router's last minutes before a hang are still lost.** This is accepted by the operator;
INC-0004 covers it with crash dumps and the console.

**`log` is reserved in every tenant's namespace**, which is a small constraint on ADR-0012 §10. A
tenant already using a first level called `log` for something else would have to move it. None does
today.

---

## Open questions

1. ~~How the bridge's credential is confined to `(index, 2)`.~~ **Answered 2026-09-22:** *one bridge
   user, routed per tenant.* The bridge holds **one** token and sets a tenant header per message.
   vmauth's `url_map` matches that header and then overwrites the partition headers with that entry's
   values, so a header the bridge sets can only select among entries the API wrote — it cannot invent a
   partition. The API adds one entry per tenant when it creates the tenant
   ([CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/) builds the user and its routing; the bridge
   fills in its token in the change after).

   The alternative, a token per tenant, was not chosen: the bridge would have to hold and refresh N
   tokens and learn about new tenants, for confinement that vmauth's config already gives.
2. ~~**Delivery guarantees.**~~ **Measured 2026-09-23** ([CHG-0021](/docs/changes/2026/0021-mqtt-log-bridge/)):
   the bridge was stopped, a QoS 1 message published to `mabell/log/ma-bell-gw-01`, and the bridge
   started again — **the message arrived**. The broker held it for the offline persistent session and
   redelivered on reconnect.

   What is still not established is the *bound*: how many messages VerneMQ will hold for an offline
   session and for how long is a setting on the broker, and the answer above is one message over
   about ten seconds. A device that logs steadily through a long outage is a different measurement,
   and the honest statement today is that a short restart loses nothing.
3. **Rate limiting per device.** Only vmauth's per-user concurrency exists (ADR-0022 §6). A chatty
   device fills its own tenant's partition. Whether the bridge needs a per-device rate limit is open.

## What would reopen this

- **Moving the store to the tenant hypervisor (Option B)**, if **both** of these hold:
  1. **The core router's `re0` still hits watchdog timeouts** over about a week after it is moved to
     Realtek's vendor driver (INC-0004 follow-up 3).
  2. **Tenant logging is a noticeable share of `re0`'s traffic.** Compare VictoriaLogs' per-tenant bytes
     ingested with `re0`'s interface counters over the same window.

  Replacing the router makes this moot. Logs are not authoritative data (ADR-0022 §6), so a move can
  start the store empty.
- **A second tenant hypervisor** changes Option B's arithmetic: local to one, routed from the rest.
- **A need for substrate logs centrally** after all, for example an incident where they were the
  missing evidence.

---

## Current state

*Updated 2026-09-23.*

- **Proposed**, and it stays Proposed until a device ships its own logs. What exists is the whole
  path, proven with a device's real credential — not the device.
- The store runs on `dv02obs001v01`. [CHG-0019](/docs/changes/2026/0019-log-store-tenant-scope/)
  stripped it to this record's scope: the syslog listener and the six substrate ingest users are
  gone, and `(0, 0)` was cleared.
- **Tenant tokens are issued.** [CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/): the API gives
  each tenant an ingest and a read token and writes the vmauth users and routes for `(index, 0..2)`,
  including the bridge's per-tenant route. eds, tdemo and mabell hold theirs.
- **The bridge is deployed** on `dv02msg001v01`
  ([CHG-0021](/docs/changes/2026/0021-mqtt-log-bridge/), 2026-09-23). It holds `+/log/#`, cannot
  publish, and carries a line from `mabell/log/ma-bell-gw-01` into `(3, 2)` where mabell reads it
  with its own token. A payload claiming another tenant changes nothing.
- **§3's reservation of the `log` level** is written and in review in the API. Until it merges,
  nothing but review stops a tenant granting something else under `log/`; the only grant that exists
  is the compliant one.
- **No device firmware publishes yet.** mabell's gateway holds `mabell/log/ma-bell-gw-01` and logs to
  serial; eds's stand has no `log/` grant at all. That is the last link, and it is work in each
  device's own repository.

### What reading a partition you have no route for does

Worth knowing before it is debugged: a read token asking for another tenant's partition is **not
refused** — vmauth's `url_map` matches the selector entries first, and a request matching none falls
to the catch-all, which is that token's own `(index, 0)`. So the caller gets **its own** logs back.
The boundary holds; the error does not exist. There is no way to express "refuse an unknown value of
this header" in a configuration that must also serve the ordinary request carrying no header at all.
