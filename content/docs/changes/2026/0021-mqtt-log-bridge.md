---
title: "CHG-0021: The MQTT Log Bridge"
weight: 21
---

# CHG-0021: The MQTT Log Bridge

| | |
|---|---|
| **Date** | 2026-09-22 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete, 2026-09-22.** Deployed on `dv02msg001v01` and verified end to end: a line published with mabell's gateway credential reached that tenant's `(3, 2)` and was read back with its own token. The broker was never restarted. Two findings, both below: a payload that claims another tenant changes nothing, and an unknown partition selector falls through to the tenant's own `(index, 0)` rather than being refused. **No device firmware publishes yet**, so ADR-0027 stays Proposed.
| **Window** | 2026-09-22 23:08 to 23:32, in two parts: the bridge, then the API |
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

All six steps are **deployed**, 2026-09-22.

| | Step | Where |
|---|---|---|
| 1 | **The service.** Subscribe, map, post; configuration from the environment, both credentials from a root-only env file | `deevnet-log-bridge`, PR #1 — **merged** |
| 2 | **The image**, built and staged like the others | `make stage`; `v0.1.0` is staged, **`v0.1.1` is what the role pins** — see below |
| 3 | **The broker account**, provisioned by the substrate with a subscribe-only grant | `deevnet.mgmt` PR #43, in the `vernemq` role |
| 4 | **The role**, deployed beside `vernemq`, reaching the store over `iot_backend -> platform` | `deevnet.mgmt` PR #43, the new `log_bridge` role |
| 5 | **Reserve `log` in the API's topic validation** (ADR-0027 §3) | `deevnet-provisioning-api` PR #14 |
| 6 | The inventory: the `log_bridges` group, the account password, and the store token moved to `all` because two hosts need it | inventory PR |

**The order it was deployed in**, because two of these depend on each other:

1. merge `deevnet-log-bridge` #2, then tag `v0.1.1` and `make stage` — the role pins that version and
   will not find a tarball for it before then
2. merge the inventory
3. `ansible-playbook playbooks/site.yml --tags mqtt-broker,log-bridge --limit dv02msg001v01` — the
   broker play writes the account, and the bridge play deploys the container that uses it, in that
   order within one run

### What the smoke test changed

The bridge's account is the one account on the broker that no tenant prefix confines, and `+/log/#`
is a shape nothing else uses. Whether VerneMQ's PostgreSQL ACL honors a single-level wildcard at the
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

### Run on the substrate, 2026-09-22

Published over TLS with **mabell's real gateway credential**, to `mabell/log/ma-bell-gw-01`. Not the
firmware — that is still to come — but the device's own account, its own topic, and the whole path
behind it.

| | Result |
|---|---|
| **A line arrives.** | It is in `(3, 2)` within seconds, read back with mabell's own token, carrying `tenant=mabell`, `device=ma-bell-gw-01` and the topic |
| **A lying payload changes nothing.** A message whose JSON said `"tenant":"eds","device":"lp-stand-01"` | landed in **mabell's** partition as `tenant=mabell`, `device=ma-bell-gw-01`. The topic decides; the payload is content |
| **A restart loses nothing.** The bridge was stopped, a QoS 1 message published, the bridge started | **It arrived.** The broker held it for the offline persistent session and redelivered on reconnect — see ADR-0027 open question 2, now answered by measurement |
| **The broker is unaffected.** | The device connected and published normally while the bridge was stopped, and the broker container was never restarted by this change |
| **No cross-tenant read.** mabell's read token asked for partitions `2-2`, `2-0` and `0-0` | It never reached account 2. See the finding below for what it got instead |
| **Idempotent.** A second full run | `changed=0` |

#### The reservation, on the live API (23:30)

Five requests the API now refuses, each with its reason, and **none of them created anything** —
mabell still has exactly one account:

| Asked for | Answer |
|---|---|
| a device publishing `log/ma-bell-gw-02` | `400` — *a device account may publish only log/ma-bell-gw-01 under the reserved log level* |
| a device publishing `log/+` | `400` — same |
| a device subscribing `log/#` | `400` — *a device account may not subscribe under the reserved log level* |
| a device subscribing `#` | `400` — same. It reaches the log space **without naming it**, which is the case a prefix test would have let through |
| a workload publishing `log/backend` | `400` — *only a device account may publish under log/* |

And the compliant shapes still pass: mabell's real grant and eds's workload account both re-applied
cleanly, no password reissued, and `terraform plan` for mabell is `No changes`.

#### Finding: an unknown selector falls through, it does not refuse

Asking with a partition selector the token has no route for — mabell's token asking for `2-2` —
returns **that tenant's own `(3, 0)`**, not a refusal. The `_stream_id` says so: every row came back
under account 3.

The security property holds: a tenant cannot reach another's partitions, which is what matters. But
the behavior is worth knowing before someone debugs it: vmauth's `url_map` matches the selector
entries first and a request that matches none falls to the catch-all, which is the tenant's own
`(index, 0)`. There is no way to express "refuse an unknown value of this header" in the same config
that must also serve a request carrying no header at all, which is the ordinary case.

### Run off the substrate, 2026-09-22

Against a throwaway VerneMQ and its auth database, with the real binary and the real account
statement — 13 checks, all passing, and each one sabotaged to watch it fail:

| | |
|---|---|
| The account statement writes the row, and **reports nothing the second time** | the idempotence guard |
| The broker accepts `+/log/#` | the open risk in this design, now closed |
| A device's log line reaches the store, under the tenant **from the topic**, with the device as a field | |
| A non-log topic the same device published is **not** carried | the scope of `+/log/#`, in one check |
| The credential is refused from another client id | the pin works |
| The account connects, may **not** publish, may **not** subscribe outside the log level | |

## Undo

Stop and remove the bridge and its account. Devices keep publishing; nothing collects their logs.
Nothing else in the store or the broker changes.

## Outcome

**Complete, 2026-09-22 23:08–23:32.** One run, `--tags mqtt-broker,log-bridge --limit
dv02msg001v01`: 107 tasks, 14 changed, none failed.

| When | Steps | What happened |
|---|---|---|
| 2026-09-22 | 1, 2 | The service merged; `v0.1.0` tagged and staged. Its smoke test then found the SUBACK defect, so `v0.1.1` was tagged and staged instead |
| 2026-09-22 23:08 | 3, 4, 6 | The broker account and the bridge deployed in one run. **The broker was not restarted** — it is up from before the change, so no device connection was disturbed |
| 2026-09-22 23:13 | Verification | A real publish with mabell's gateway credential arrived in `(3, 2)` and was read back with mabell's own token |
| 2026-09-22 23:16 | Verification | A second run: **`changed=0`**. The guarded upsert converges rather than rewriting the password hash every run |
| 2026-09-22 23:28 | 5 | API **v0.7.0** deployed, and the reservation refuses all five misuses while the compliant grants still pass |

**Step 5 deployed at 23:28**, after the rest: API **v0.7.0** on `dv02prv001v01`, which refuses a
grant that misuses the level. It was never a prerequisite for the bridge — the bridge carries what
the broker allows, and the only grant under `log/` was already the compliant one — so it went last
and on its own.

### What the account looks like on the broker

```
substrate-log-bridge | cid=deevnet-log-bridge | pub=[] | sub=[{"pattern": "+/log/#"}]
```

Beside three tenant accounts, all with `cid=*` and their own prefixes. It is the only row with a
pinned client id and the only one with no publish grant.

### Departures from the plan

- **`v0.1.1`, not `v0.1.0`.** Testing the account off the substrate found a defect in the bridge
  itself — see [What the smoke test changed](#what-the-smoke-test-changed) — and the version that
  deployed is the one that reads the SUBACK.
- **The live "the bridge cannot publish" check was not run.** Its client id is pinned, so a second
  client using it would evict the running bridge to prove something the smoke test already proves
  against a throwaway broker, and the deployed row has an empty publish list. Recorded as covered
  off-substrate rather than claimed here.

## Follow-ups

- [ ] **The bridge's password hash is `$2a$06$`, the API's accounts are `$2a$12$`.** pgcrypto's
  `gen_salt('bf')` defaults to cost 6, and the role takes the default where the API asks for 12
  (ADR-0012 §8). Not a practical risk — the password is 48 random characters — but it is an
  inconsistency, and worth knowing that **fixing it needs more than changing the call**: the role's
  idempotence guard verifies with `crypt(pw, stored)`, which succeeds whatever cost the stored hash
  used, so a cost change alone never rewrites an existing row.
- [ ] **The firmware.** Nothing publishes under `log/` by itself yet: mabell's gateway holds the
  grant and logs to serial only, and its MQTT client is unused. Until a device does this on its own,
  ADR-0027 stays Proposed.
- [ ] **eds has no `log/` grant yet.** mabell's gateway has one; adding eds's stand is a change in
  that tenant's own Terraform, not here.
- [ ] Per-device rate limiting, if a device proves chatty (ADR-0027 open question 3).
- [ ] The device firmware that publishes these logs, in each device's own repository.
