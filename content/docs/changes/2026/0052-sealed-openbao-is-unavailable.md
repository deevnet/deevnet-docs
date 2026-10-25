---
title: "CHG-0052: A Sealed OpenBao Is Unavailable, Not a Lost Secret"
weight: -52
---

# CHG-0052: A Sealed OpenBao Is Unavailable, Not a Lost Secret

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. One API release and deploy. First of the tenant PKI changes: before [CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/) |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API); `dv02idn001v01` (OpenBao), sealed only for the test |
| **Automation** | `deevnet-provisioning-api`; `deevnet.mgmt` `site.yml --tags deevnet-api` |
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

## Scope

**In scope:** the OpenBao client's error types; the store's `open` and `openOne` and every caller
(tenant secrets, Wi-Fi keys, admission keys); the minting paths that re-mint an empty secret; the
readiness report.
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

### Step 4: Release and deploy

Tag the release, deploy with `site.yml --tags deevnet-api`.

**Verify:** `/readyz` is `200`; every tenant's reconcile succeeds; validation plan V13's API half
passes against the sealed test store.

## Verification

V13's API half passes: a tenant request against a sealed store is refused, with no secret marked,
emptied or re-minted.

## Undo

Deploy the previous release. Nothing is migrated, so the undo is the deploy.

## To discover

- What OpenBao returns for Transit decrypt while sealed, on the running version: status and body,
  confirmed against the test store, not assumed.
