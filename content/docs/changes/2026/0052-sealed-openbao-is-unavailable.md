---
title: "CHG-0052: A Sealed OpenBao Is Unavailable, Not a Lost Secret"
weight: -52
---

# CHG-0052: A Sealed OpenBao Is Unavailable, Not a Lost Secret

| | |
|---|---|
| **Date** | 2026-10-25 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete, 2026-10-25.** API v0.13.0 is deployed on `dv02prv001v01` |
| **Window** | Unscheduled. One API release and deploy. First of the tenant PKI changes: before [CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/) |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API); `dv02idn001v01` (OpenBao), sealed only for the test |
| **Automation** | `deevnet-provisioning-api` ([#32](https://github.com/deevnet/deevnet-provisioning-api/pull/32)); `deevnet.mgmt` ([#86](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/86)) `site.yml --tags deevnet-api` |
| **Risk** | Medium. Most likely to go wrong: a decrypt that genuinely fails (a rebuilt Transit key) is mistaken for a sealed store, and the documented way back for a tenant, supplying its secrets again, stops working |
| **Related changes** | [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/), [CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/) |
| **Related incidents** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) |
| **Related runbooks** | [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/) |

---

## Summary

When a stored tenant secret will not open, the Deevnet API treats it as lost: it marks the tenant's
TSIG and state secrets unreadable, so the tenant is told to supply them again, and it empties log
tokens, the dashboard password, Wi-Fi keys and admission keys, which are re-minted on the next ensure.
That is right for what it was written for, a Transit key rebuilt under a new key (ADR-0016 §6). It is
wrong for a sealed OpenBao, where nothing is lost: a re-minted log token or Wi-Fi key replaces one
that still works. [ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/)
§3 makes this a requirement before OpenBao is ever sealed on purpose
([review R3-1](/docs/architecture/reviews/2026-10-tenant-pki/), phase P0).

**The rule after this change:** OpenBao sealed or unreachable means the API refuses tenant work
before it changes anything, with an error that says so. Only a decrypt that OpenBao answers and
refuses is a lost secret.

## Goal

- The API's OpenBao client tells **unavailable** (sealed, unreachable, a server error) apart from
  **refused** (a ciphertext the key will not open).
- An unavailable store fails the request with `503` and a message naming OpenBao as sealed or
  unreachable. No secret is marked unreadable, emptied or re-minted.
- `/readyz` reports OpenBao as well as the database, so a sealed store is visible without a tenant
  request.
- A refused decrypt keeps today's behavior: the tenant's way back is unchanged.
- A tenant token presented while OpenBao is sealed is answered `503`, not `401`: the token is
  fine, and a tenant told otherwise would chase the wrong fault.
- **The API starts while OpenBao is sealed.** Today it exits when it cannot read its backend
  credentials and restarts until OpenBao opens. Once OpenBao is sealed by default (CHG-0053), that
  would be every restart outside a work session. It serves readiness, answers `503` on `/v1`, and
  reads its credentials as soon as OpenBao opens.
- The `deevnet_api` role's readiness wait stops on a sealed OpenBao with a plain message.

## Scope

**In scope:** the OpenBao client's error types; the store's `open` and `openOne` and every caller
(tenant secrets, Wi-Fi keys, admission keys); the minting paths that re-mint an empty secret;
tenant authentication; the readiness report; startup; the `deevnet_api` role's readiness wait.
**Out of scope:** changing the seal (CHG-0053); the Ansible plays' sealed stop (CHG-0053).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A real lost secret reported as unavailable | the API | Only `503`, a network error or a timeout is unavailable; a `400` from Transit decrypt stays a lost secret. Both are tested |
| A sealed store mid-request leaves a half-written record | the API | Every secret is opened before anything is written; the request stops at the first unavailable one |
| Readiness turns red and the API is restarted for nothing | `dv02prv001v01` | `/readyz` reports OpenBao; `/healthz` stays liveness only and never touches it |

## Prerequisites

- [ ] A test OpenBao, sealable at will, for the integration tests (never the identity VM)
- [ ] The API's current release noted for the undo

## Procedure

### Step 1: The client says why it failed

`Open`, `Seal`, `Wrap`, KV reads and signing return an `ErrUnavailable` for a sealed or unreachable
OpenBao, distinct from a refused decrypt.

**Verify:** unit tests against a stub answering `503 Vault is sealed`, a closed port, and `400` on
decrypt.

### Step 2: The store refuses instead of forgetting

`openOne` returns an unavailable error to its caller instead of an empty value; `open` stops at it;
the tenant, Wi-Fi key and admission key reads pass it up; no ensure re-mints a secret it could not
read.

**Verify:** integration test against the test OpenBao, sealed: a tenant read, an ensure and a Wi-Fi
key read each return `503`, and the database rows are byte-for-byte unchanged.

### Step 3: Readiness names OpenBao

`/readyz` checks OpenBao's health endpoint (no token) and reports `openbao: sealed`,
`unreachable` or `ok`.

**Verify:** readiness is `503` with `openbao: sealed` against the sealed test store, `200` unsealed.

### Step 4: Startup

The API starts with OpenBao sealed and waits for it in the background, as it waits for its
database migrations.

**Verify:** started against a sealed store, readiness is `503 openbao: sealed` and `/v1` is `503`;
unsealed, both turn `200` with no restart.

### Step 5: Release and deploy

Tag the release; merge the role's change; deploy with `site.yml --tags deevnet-api`.

**Verify:** `/readyz` is `200`; every tenant's reconcile succeeds; validation plan V13's API half
passes against the sealed test store.

## Verification

V13's API half passes: a tenant request against a sealed store is refused, with no secret marked,
emptied or re-minted.

## Undo

Deploy the previous release. Nothing is migrated, so the undo is the deploy.

## Outcome

Built in [deevnet-provisioning-api#32](https://github.com/deevnet/deevnet-provisioning-api/pull/32)
and released as **v0.13.0**; the role's readiness wait in
[deevnet.mgmt #86](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/86) and the
version in [#88](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/88). Deployed
with `site.yml --tags deevnet-api --limit deevnet_api`.

| Step | Result |
|---|---|
| 1–3 | Unit tests against a stub that answers `503`, a closed port and `400`. The store test against a throwaway PostgreSQL 17.11 **fails** on the old `openOne` and passes on the new one. Against a throwaway OpenBao 2.6.2 in dev mode: a ciphertext the key refuses is `400`; sealed, decrypt, encrypt and AppRole login are `503 Vault is sealed`, and readiness reports `sealed` |
| 4 | The binary against that OpenBao, sealed, then unsealed, then sealed again: readiness `503 openbao: sealed`, then `200`, then `503`; `/v1` `503`, then `200`, with no restart. V13's API half passes |
| 5 | On `dv02prv001v01`: `/version` is v0.13.0 (commit `5659403`); `/readyz` is `200` with `database: ok, openbao: ok`; `eds`, `tdemo`, `mabell` and `cdeever` each read back `ready` with their secrets stored |

### Departures from the plan

- **The first staging failed**: the image build filled the Builder's `/home`, which holds podman's
  storage. Leftover build containers and untagged images were removed and the build rerun.
- **No reconcile was run after the deploy.** Each tenant's read opened its stored secrets, which is
  what this change touched; each tenant's next apply is its reconcile.

## Follow-ups

- Podman's storage on the Builder is on a 20 GB `/home`, which image builds have now filled twice.

## To discover

- ~~What OpenBao returns for Transit decrypt while sealed.~~ Found while building, against a
  throwaway OpenBao 2.6.2: a ciphertext the key refuses is `400 cipher: message authentication
  failed`; sealed, decrypt, encrypt and AppRole login are all `503 Vault is sealed`. The client
  treats any `5xx` or transport error as unavailable.
