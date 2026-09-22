---
title: "CHG-0020: The API Issues Tenant Log Tokens"
weight: 20
---

# CHG-0020: The API Issues Tenant Log Tokens

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Not yet scheduled |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the API), `dv02obs001v01` (the store; gains a writer), tenants `tdemo` and `eds` |
| **Automation** | `deevnet.mgmt` `site.yml` (`deevnet_api`, `victorialogs`); `deevnet-provisioning-api`; `terraform-provider-deevnet`; inventory `mobile` |
| **Risk** | Medium. The API gains a second backend, so a fault there fails a tenant's `terraform apply`. The store's `auth.yml` gains a second author, and getting that wrong would drop the operator's user or a tenant's. |
| **Related changes** | [CHG-0018](/docs/changes/2026/0018-central-log-store/) (built the store), [CHG-0019](/docs/changes/2026/0019-log-store-tenant-scope/) (made it tenants-only), [CHG-0016](/docs/changes/2026/0016-broker-accounts/) (the forced-SSH pattern this copies) |
| **Related incidents** | None |
| **Related runbooks** | [ADR-0027: Tenant Log Store](/docs/architecture/decisions/0027-tenant-log-store/), [ADR-0022 §3](/docs/architecture/decisions/0022-central-logging/) |

---

## Summary

The log store has one user, the operator's. No tenant can write to it, so ADR-0027's design has
never been exercised. This change makes the Deevnet API issue each tenant a **log ingest token** and
a **log read token**, and write the matching vmauth users into the store, the same way CHG-0016 made
it write broker accounts.

After this, a tenant's `terraform apply` yields credentials its workloads can ship logs with, and the
store stops being an empty box.

## Goal

| | |
|---|---|
| A new tenant | gets an ingest token and a read token in its create response, and in its Terraform state |
| `tdemo` and `eds` | get theirs through `reconcile`, without being rebuilt |
| The ingest token | writes `(index, 0)` and nothing else |
| The read token | reads `(index, 0)`, `(index, 1)` and `(index, 2)`, and nothing else |
| Cross-tenant | one tenant's token cannot read or write another's partition, **measured** |
| `auth.yml` | has the operator's user, both users per tenant, and survives an Ansible run and a writer run in either order |
| The API | refuses to issue when the store is unreachable, with the reason, rather than issuing a token nothing honours |

## Scope

**In scope:** the API's new backend and credential, the writer on `obs`, the provider attributes, the
Ansible and inventory work, and issuing for the two existing tenants.

**Out of scope:**
- the MQTT bridge and `(index, 2)`'s writer (the next change), though the writer's file format and the
  bridge user's routing are built here so the bridge only has to fill in its token
- anything on a device
- Grafana (ADR-0024)

## Design

### Where it differs from the broker account

The broker writer sends a **bcrypt hash**: the far end never learns a password. A vmauth user needs
the **bearer token itself**, because that is what it compares against. So:
- the token is stored **sealed** (OpenBao Transit), like the Wi-Fi PSK, not hashed like the broker
  password
- the writer receives the token, so the writer is as sensitive as the store's config file

Everything else follows CHG-0016: a fixed-path config, a forced command pinned with
`command=`, `restrict` and `from=`, one request and one answer on stdin/stdout, and the API's
ordering discipline (row first as `provisioning`, then the writer, then `ready`).

### Who owns `auth.yml`

Both Ansible and the API write to the store's configuration, so neither owns the file:

- **Ansible owns `base.yml`**: the operator's read user, the backend URL and the bridge user's token.
- **The API's writer owns `users.d/<tenant>.json`**: one small file per tenant with its index and its
  two tokens.
- **`auth.yml` is generated** from `base.yml` plus every fragment, by the writer, and by the Ansible
  role. Both render the same file from the same inputs, so an Ansible run cannot drop a tenant and a
  writer run cannot drop the operator.
- The writer reloads vmauth through its **loopback internal listener** (`127.0.0.1:8426/-/reload`),
  which needs no root.

### No new zone rule

`prv` and `obs` are both on Platform, so the API reaches the writer on the **same segment**: no
router, no rule. This is unlike CHG-0016, which crossed `platform -> iot_backend` and needed one. The
host's own firewall still applies, and sshd on `obs` is already open to the zone.

### The bridge user, built now and used later

The generated `auth.yml` carries one **bridge user**, whose token comes from `base.yml`, with one
`url_map` entry per tenant: a request carrying that tenant's header is routed to `(index, 2)`, and
vmauth overwrites the partition headers with the entry's values. That answers ADR-0027's open
question 1. The bridge itself arrives in the next change; until its token is set, the user exists
with a token nothing holds.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A generated `auth.yml` drops the operator or a tenant | `obs` | one renderer, two callers, same inputs; the writer validates the rendered file before replacing it, and reloads only after |
| A token is issued that the store does not honour | API | the row is written `provisioning` first; the writer runs; only then `ready`. A writer failure returns 502 **with** the credential, as broker accounts do |
| The store is down during a tenant apply | tenant | the API returns the reason; the tenant's apply fails cleanly rather than storing a token nothing honours |
| The writer leaks a token into a log | `obs` | it echoes one JSON response and never the request; detail goes to stderr for the API's log |
| An Ansible run and a writer run race | `obs` | the writer writes a temp file and renames it; the role does the same |

## Prerequisites

- [ ] Vault decrypted, for the API's new SSH key and the bridge token
- [ ] The store healthy (CHG-0019 verification)

## Procedure

### Step 1: The writer's key

Generate an ed25519 key pair for the API. The private half goes in the vault as
`vault_deevnet_api_log_writer_key`; the public half goes in `group_vars/observability_store/vars.yml`
as `victorialogs_writer_public_key`, with `victorialogs_writer_from` set to the API's address.

**Stop** and have the operator vault, commit and push before anything uses it.

### Step 2: The API

New, copying `brokeracct`/`brokerwriter` almost exactly:
- `internal/logauth/contract.go` — the wire contract, with its own validation
- `cmd/deevnet-log-user/` — the writer binary, a host binary like `deevnet-broker-account`
- `internal/backend/logwriter/` — the SSH client, with the host key pinned and its algorithm with it
- `internal/tenant/logtokens.go` — issue, reissue, delete, and `StepLogStore`
- `internal/store/logtokens.go` + `migrations/0006_log_tokens.sql` — sealed tokens
- `internal/server/tenants.go` — the tokens ride in the tenant view, as TSIG and the state key do
- `cmd/deevnet-api/config.go` — `DEEVNET_LOG_WRITER_ADDR` gates the feature, as the broker's does

**Verify:** `make test`, `make vet`.

### Step 3: The provider

`deevnet_tenant` gains `log_ingest_token` and `log_read_token`: computed, sensitive,
`UseStateForUnknown`, never blanked by `ModifyPlan`, exactly like the broker account's password.

### Step 4: Ansible and inventory

- `victorialogs` gains `writer.yml` (user, binary, config, `authorized_keys`, health probe) and
  renders `base.yml`, `users.d/` and `auth.yml`.
- `deevnet_api` gains the `DEEVNET_LOG_*` environment and pins `obs`'s host key by slurping it.
- The bridge token is generated and vaulted with the writer's key in Step 1.

### Step 5: Deploy and issue

Build and stage the API and the writer, deploy the store and the API, then:
- `POST /v1/tenants/tdemo/reconcile` and the same for `eds`, which returns their tokens
- the tenants' Terraform picks them up on the next apply

## Verification

1. **A tenant can write and read its own partition.** With `eds`'s ingest token, write a line; with
   its read token, read it back from `(2, 0)`.
2. **Cross-tenant is refused.** `tdemo`'s read token, given `eds`'s partition headers, returns
   `tdemo`'s partition or nothing — never eds's line. The same for ingest.
3. **The ingest token cannot read**, and the read token cannot write: 400 `missing route`.
4. **Both authors survive.** Run the Ansible role, then the writer, then the role again. After each,
   `auth.yml` still has the operator's user and every tenant's users.
5. **A store outage is honest.** Stop vmauth, reconcile a tenant, and see a 502 naming the step, not a
   token that works nowhere.
6. **The API's `/version`** matches the deployed tag, as its role already asserts.

## Undo

- Redeploy the previous API image and the previous role.
- The writer's `authorized_keys` entry is removed by clearing `victorialogs_writer_public_key`.
- Tenant rows can stay: a token nothing honours is inert, and re-running the writer restores them.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] **The MQTT bridge** (ADR-0027 §4), which fills in the bridge user's token.
- [ ] **Tenant repos** pick the tokens up: `eds` ships its workloads' logs.
