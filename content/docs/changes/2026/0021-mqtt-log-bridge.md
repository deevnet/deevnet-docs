---
title: "CHG-0021: The MQTT Log Bridge"
weight: 21
---

# CHG-0021: The MQTT Log Bridge

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Not yet scheduled |
| **Site** | mobile |
| **Systems** | `dv02msg001v01` (runs the bridge, beside the broker), `dv02obs001v01` (receives), the broker's auth database |
| **Automation** | `deevnet.mgmt`: a new role, deployed beside `vernemq`. The image comes from wherever the bridge's source ends up living (see *The one open decision*) |
| **Risk** | Low to the substrate: the bridge only reads from the broker and writes to the store. The risk it carries is a subscribe-everything account, which is why its confinement is stated and tested here. |
| **Related changes** | [CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/) (built the bridge's user and routing), [CHG-0015](/docs/changes/2026/0015-vernemq-broker/) (the broker), [CHG-0016](/docs/changes/2026/0016-broker-accounts/) (how accounts are written) |
| **Related incidents** | None |
| **Related runbooks** | [ADR-0027 §3, §4](/docs/architecture/decisions/0027-tenant-log-store/) |

---

## Summary

[ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/) says a tenant's edge devices report
their logs over MQTT, and that a substrate bridge carries them into that tenant's `(index, 2)`
partition. CHG-0020 built everything on the store's side: the bridge's user exists, with one route
per tenant, selected by a header. What is missing is the bridge.

This change builds and deploys it.

## Goal

| | |
|---|---|
| A device publishing to `<tenant>/log/<device>` | has that line in its tenant's `(index, 2)` within seconds |
| The tenant | reads it with its own read token, and no other tenant can |
| The bridge | holds one broker account that may **subscribe only**, to `+/log/#`, and one store token |
| A message's tenant | comes from the broker-enforced topic prefix, never from anything in the payload |
| The bridge down | loses nothing that was published with QoS 1 while its session persists; what it does lose is stated, not discovered |
| The broker and the store | are unaffected by a bridge that is stopped, restarted or absent |

## Scope

**In scope:** the bridge service, its broker account, its deployment beside the broker, and the
end-to-end test with a real device.

**Out of scope:**
- device firmware (the devices' own repositories)
- tenant workload logs, which go straight to the store with the tenant's own ingest token
- anything about `(index, 0)` or `(index, 1)`

## The one open decision

**Where the bridge's source lives.** Three homes were considered:

| | Against it |
|---|---|
| `deevnet-container-image-factory` | Its README is explicit: it is for *"software the substrate runs but does not write"*, built from upstream source whose binaries we may not use. The bridge is ours. |
| `deevnet-provisioning-api` | That repository is **provisioning-only**, and nothing at runtime depends on it. The bridge is a runtime service, and putting it there blurs the one boundary that repository exists to keep. |
| **A new repository, `deevnet-log-bridge`** *(recommended)* | One more repository to run, and a new image build path. |

The recommendation is the new repository: it is the only option that does not weaken a boundary
another repository is built on. **Creating it is the operator's call**, which is why this record
names the decision rather than assuming it.

## Design

### What it does

1. Subscribes to `+/log/#` on the broker, with QoS 1 and a persistent session.
2. Takes the tenant from the **first topic level**. The broker enforces each account's prefix
   (ADR-0012 §10), so a message under `eds/…` was published by an `eds` account. That is the whole
   reason this mapping is trustworthy, and it is what a collector reading a third-party service's
   logs could never have.
3. Turns the message into a log line: a JSON payload becomes fields, anything else becomes the
   message text.
4. Adds `tenant`, `device` (the last topic level), and the receive time if the payload carries none.
5. POSTs it to the store with its own token and `X-Deevnet-Tenant: <tenant>`.

vmauth matches that header against the routes CHG-0020 wrote, then **overwrites** the partition
headers with that route's values. So the bridge selects among tenants the API has written and can
reach no other partition, and a device cannot reach any partition at all.

### What it must not do

- **It never trusts the payload for identity.** A device that puts `"tenant": "someone-else"` in its
  JSON changes nothing: the partition comes from the topic.
- **It never publishes.** Its broker account has no publish grant.
- **It is not in a device's path.** A stopped bridge loses logs; it does not stop a device working,
  and the broker keeps accepting messages either way.

### Its two credentials

| | What it is | Written by |
|---|---|---|
| Broker account | subscribe-only, `+/log/#`, no publish | the substrate, like the broker's own database roles — **not** through the API, because it is not a tenant's account |
| Store token | the bridge user's bearer token | already in the vault as `vault_victorialogs_bridge_token` (CHG-0020) |

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The bridge account is a subscribe-everything account | broker | subscribe-only, one topic level, no publish; it sits beside the broker, which sees every message anyway |
| A device fills its tenant's partition | store | it can only fill **its own** tenant's; per-device limits are ADR-0027 open question 3 |
| A tenant's logs land in another tenant's partition | bridge | the tenant comes from the enforced prefix; tested with two tenants, and with a device that lies in its payload |
| Messages lost while the bridge is down | bridge | QoS 1 and a persistent session; what the broker queues and for how long is confirmed against VerneMQ's documentation, not assumed |

## Prerequisites

- [ ] CHG-0020 deployed: the bridge user exists in the store with a route per tenant
- [ ] The source's home decided (above)
- [ ] At least one device publishing to `<tenant>/log/<device>`

## Procedure

1. **The service**, wherever it lives: subscribe, map, post, with its configuration from the
   environment and its two credentials from a root-only env file.
2. **The image**, built and staged like the others.
3. **The broker account**, provisioned by the substrate with a subscribe-only grant.
4. **The role**, deployed beside `vernemq` on the messaging VM, reaching the store over
   `iot_backend -> platform`, which is already declared.
5. **Reserve `log` in the API's topic validation**, so a tenant cannot grant a device something
   under `log/` that the bridge would then carry for it (ADR-0027 §3).

## Verification

1. **A real device's line arrives.** Publish from `lp-stand-01` to `eds/log/lp-stand-01`; read it
   back with eds's read token from `(2, 2)`.
2. **The other tenant sees nothing.** `tdemo`'s read token returns nothing for it.
3. **A lying payload changes nothing.** Publish `{"tenant":"tdemo","_msg":"x"}` to `eds/log/…`; it
   lands in eds's partition.
4. **The bridge cannot publish.** Its account is refused when it tries.
5. **A restart loses nothing** that was published with QoS 1 while it was down, within whatever the
   broker's queue actually holds — measured, and written down here.
6. **The broker is unaffected** by the bridge being stopped: a device still connects and publishes.

## Undo

Stop and remove the bridge and its account. Devices keep publishing; nothing collects their logs.
Nothing else in the store or the broker changes.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] Per-device rate limiting, if a device proves chatty (ADR-0027 open question 3).
- [ ] The device firmware that publishes these logs, in each device's own repository.
