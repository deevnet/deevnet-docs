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
| **Status** | **In progress, 2026-09-22.** Everything is built and in review: the service, its smoke test, the broker account, the deploy role, the inventory, and the API's reservation of the `log` level. Nothing is deployed. Building it found one defect in the bridge itself, described under [What the smoke test changed](#what-the-smoke-test-changed). |
| **Window** | Not yet scheduled |
| **Site** | mobile |
| **Systems** | `dv02msg001v01` (runs the bridge, beside the broker), `dv02obs001v01` (receives), the broker's auth database |
| **Automation** | `deevnet.mgmt`: a new role, deployed beside `vernemq`. The image is built and staged by [deevnet-log-bridge](https://github.com/deevnet/deevnet-log-bridge) |
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

## Where the bridge's source lives — decided 2026-09-22

**A new repository, [deevnet-log-bridge](https://github.com/deevnet/deevnet-log-bridge)**, created on
2026-09-22. Its first code is open for review as PR #1. Three homes were considered:

| | Against it |
|---|---|
| `deevnet-container-image-factory` | Its README is explicit: it is for *"software the substrate runs but does not write"*, built from upstream source whose binaries we may not use. The bridge is ours. |
| `deevnet-provisioning-api` | That repository is **provisioning-only**, and nothing at runtime depends on it. The bridge is a runtime service, and putting it there blurs the one boundary that repository exists to keep. |
| **A new repository, `deevnet-log-bridge`** *(chosen)* | One more repository to run, and a new image build path. |

The new repository is the only option that does not weaken a boundary another repository is built
on, and it matches what the estate already does with software it writes: the provisioning API builds
and stages its own image from its own repository. ADR-0027 said the factory would build it; that
sentence is corrected.

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

- [x] CHG-0020 deployed: the bridge user exists in the store with a route per tenant
- [x] The source's home decided (above), and the service written: PR #1 in that repository, merged
- [ ] At least one device publishing to `<tenant>/log/<device>`. **mabell's gateway is granted
  `mabell/log/ma-bell-gw-01` and eds's stand is not granted anything under `log/` yet**; neither
  device's firmware publishes there, which is the work in each device's own repository.

## Procedure

Every step below is **built and in review** as of 2026-09-22. None is deployed.

| | Step | Where |
|---|---|---|
| 1 | **The service.** Subscribe, map, post; configuration from the environment, both credentials from a root-only env file | `deevnet-log-bridge`, PR #1 — **merged** |
| 2 | **The image**, built and staged like the others | `make stage`; `v0.1.0` is staged, **`v0.1.1` is what the role pins** — see below |
| 3 | **The broker account**, provisioned by the substrate with a subscribe-only grant | `deevnet.mgmt` PR #43, in the `vernemq` role |
| 4 | **The role**, deployed beside `vernemq`, reaching the store over `iot_backend -> platform` | `deevnet.mgmt` PR #43, the new `log_bridge` role |
| 5 | **Reserve `log` in the API's topic validation** (ADR-0027 §3) | `deevnet-provisioning-api` PR #14 |
| 6 | The inventory: the `log_bridges` group, the account password, and the store token moved to `all` because two hosts need it | inventory PR |

**The order to deploy in**, because two of these depend on each other:

1. merge `deevnet-log-bridge` #2, then tag `v0.1.1` and `make stage` — the role pins that version and
   will not find a tarball for it before then
2. merge the inventory
3. `ansible-playbook playbooks/site.yml --tags mqtt-broker,log-bridge --limit dv02msg001v01` — the
   broker play writes the account, and the bridge play deploys the container that uses it, in that
   order within one run

### What the smoke test changed

The bridge's account is the one account on the broker that no tenant prefix confines, and `+/log/#`
is a shape nothing else uses. Whether VerneMQ's PostgreSQL ACL honours a single-level wildcard at the
**first** level was not a thing to find out on the live broker, so `smoke-test.sh` stands up a
throwaway broker and database, writes the account with the same statement the role writes, and runs
the real binary against it.

**It does work** — one pattern covers every tenant, and the account is confined to it. Then the same
test, run against an account whose ACL did *not* cover the filter, found something worse than the
question it was asked:

> A broker that refuses a filter answers `0x80` for it in an otherwise **successful** SUBACK and
> leaves the connection up. The client library does not call that an error.

The bridge logged `subscribed`, carried nothing, and reported itself healthy — and the deploy role's
verification keyed on exactly that log line, so a refused subscription would have deployed green.
`v0.1.1` reads the SUBACK: a refused filter is logged as a refusal with the reason, and `/healthz`
answers `503` until the subscription is real. The role now asks the bridge whether it *holds* its
subscription rather than whether the container is up.

## Verification

### Already run, off the substrate (2026-09-22)

Against a throwaway VerneMQ and its auth database, with the real binary and the real account
statement — 13 checks, all passing, and each one sabotaged to watch it fail:

| | |
|---|---|
| The account statement writes the row, and **reports nothing the second time** | the idempotence guard, so `site.yml` neither reports changed for ever nor rewrites the password hash on every run |
| The broker accepts `+/log/#` | the open risk in this design, now closed |
| A device's log line reaches the store, under the tenant **from the topic**, with the device as a field | |
| A non-log topic the same device published is **not** carried | the scope of `+/log/#`, in one check |
| The credential is refused from another client id | the pin works |
| The account connects, may **not** publish, may **not** subscribe outside the log level | |

Also checked against the live estate: every value the role derives (broker `ssl://10.20.35.20:8883`,
store `https://dv02obs001v01.mobile.deevnet.net:8427`, both credentials present), and that the
messaging VM **resolves and reaches** the store on 8427 over `iot_backend -> platform`.

### Still to run, on the substrate

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

- [ ] **eds has no `log/` grant yet.** mabell's gateway has one; adding eds's stand is a change in
  that tenant's own Terraform, not here.
- [ ] Per-device rate limiting, if a device proves chatty (ADR-0027 open question 3).
- [ ] The device firmware that publishes these logs, in each device's own repository.
