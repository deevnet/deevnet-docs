---
title: "CHG-0060: An Operator Reissue of a Tenant's State Secret"
weight: -60
---

# CHG-0060: An Operator Reissue of a Tenant's State Secret

| | |
|---|---|
| **Date** | 2026-11-09 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete, 2026-11-09.** API v0.19.0 deployed on `dv02prv001v01`; tdemo reissued a state secret, its old one refused |
| **Window** | 2026-11-09, in an OpenBao work session. One API deploy; no tenant's secret changes until the operator asks for it |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API); the state store on the same VM |
| **Automation** | `deevnet-provisioning-api` (v0.19.0), `deevnet.mgmt` `site.yml --tags deevnet-api`, `make reissue-state-secret`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Most likely to go wrong: a tenant given a new secret restores from its old state, which puts the old secret back and locks it out again. The handover file and the runbook say not to |
| **Related changes** | [CHG-0038](/docs/changes/2026/0038-reconcile-restores-everything/) (split from it), [CHG-0040](/docs/changes/2026/0040-device-secrets-in-tenant-code/) (moves the secret out of state) |
| **Related incidents** | None |
| **Related runbooks** | [Lost State or Credentials](/docs/runbook/tenant/recovery/lost-credentials/) |

---

## Summary

A tenant's state-store keys live inside the state they unlock. A tenant that loses its copy can't
read its own state, and nothing on the site gives the secret back: a reconcile deliberately doesn't
return it ([2026-10 review: T2](/docs/architecture/reviews/2026-10-rebuild-and-access/#t2-state-key-recovery)).

This change adds the reissue the review's response chose. An operator-only route mints a new secret,
records it in the registry, sets it on the store and returns it. The operator hands it over in a
file, like an enrollment token. The old secret stops working. The stored secret is still never
returned by any route.

It was a goal of CHG-0038 and is split out because it stands alone and is small.

## Goal

- `make reissue-state-secret NAME=<tenant>` gives a tenant a new state secret in
  `~/<tenant>-state-secret.txt` (mode 0600), as `.backend.env` lines.
- The old secret is refused by the store; the new one reads the tenant's state.
- No other secret of the tenant changes.

## Scope

**In scope:** `POST /v1/tenants/{name}/state-secret` in the API; `scripts/tenant-state-secret.sh` and
its `make` target in `deevnet.mgmt`; the runbook.
**Out of scope:** the provider. The tenant's Terraform state keeps the old secret, and a restore sends
back what state holds, whose secrets win (ADR-0015 §4). Rather than release a provider that lets a
tenant supply the new secret, the runbook says not to restore from old state, and CHG-0040 moves the
secret out of state.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A tenant restores from state that holds the old secret | the tenant | The handover file and the runbook say not to; CHG-0040 ends it |
| The store refuses the new secret after the registry recorded it | the state store | No secret is returned. The registry is written first, so a reconcile or a second reissue puts the store right; the other order would let a reconcile put the old secret back |
| The API holds secrets for the tenant it can't read | the registry | The reissue refuses: writing the row would store them empty. The tenant supplies them again first |
| Everyone holding the old secret loses access, CI included | the tenant | The operator target says so and asks for the name to be typed back |

## Prerequisites

- [ ] The API pull request merged and released; `make stage`
- [ ] Vault decrypted; collections built; the `deevnet.mgmt` pull request merged

## Procedure

| Step | What | Check |
|---|---|---|
| 1 | The API route, built and tested off the site | `make test` and `make test-integration` pass; against a real MinIO, the old secret is refused after a new one is set |
| 2 | Release, `make stage`, set `deevnet_api_version`, `site.yml --tags deevnet-api` | `/version` answers the new version; `make reconcile NAME=--all` is `ok` for every tenant |
| 3 | `make reissue-state-secret NAME=tdemo` | The handover file is 0600 and holds the new secret; tdemo's old `.backend.env` is refused and the new one reads its state |
| 4 | The docs | *Lost State or Credentials* gives the reissue as the way back; the API's page lists the route |

**Rollback:** redeploy the previous API version. A secret already reissued stays in force: it is in
the registry, and the previous version reconciles with what the registry holds.

## Verification

An operator gives tdemo a new state secret, and tdemo reads its state with it and not with the old one.

## Outcome

**An operator can now give a tenant a new state secret, and the old one stops working.** Every step
passed but one check of step 3, which tripped over tdemo's own unapplied code rather than the
reissue. The logs are in `migration-logs/chg0060-2026-11-09/` on the Builder.

| Step | Result |
|---|---|
| 1 | API pull request 53 and `deevnet.mgmt` pull request 107 merged. `make test` and `make test-integration` passed; against a real MinIO, the old secret is refused once a new one is set |
| 2 | v0.19.0 tagged on the release merge, staged, and deployed. `/version` answers v0.19.0 and `/readyz` is ok; `make reconcile NAME=--all` reconciled tdemo, eds, mabell and cdeever |
| 3 | `make reissue-state-secret NAME=tdemo` wrote the handover file, mode 0600. tdemo's old keys read its state before and were refused after, with 403 `SignatureDoesNotMatch`; the new keys read it. The handover file was deleted once the keys were in place |
| 4 | *Lost State or Credentials* gives the reissue as the way back; *Tenant Admission* has the operator's procedure; the Deevnet API page and the Software Catalog list it |

### Departures from the plan

- **tdemo's plan was not clean, for reasons that predate this change.** Its repository has moved on
  from what it last applied: it replaces the `app` workload with `backend` and adds devices, a Wi-Fi
  key and broker accounts, and its outputs fail on resources that don't exist yet. The only change a
  refresh found on the tenant itself was its state endpoint, from the move to the service name. Nothing
  touched the state secret. tdemo was not applied, which would have destroyed its workload.
- **tdemo's working copy needed `terraform init -reconfigure`** before the baseline, because its backend
  block had changed since its last init. No state moved.

## To close

**What is left before this change closes, from its procedure and verification.**

- [x] Step 1: the API route and the operator target merged, tests passing
- [x] Step 2: the API released and deployed; every tenant reconciles `ok`
- [x] Step 3: tdemo reissued; the old secret refused, the new one reads its state
- [x] Step 4: *Lost State or Credentials* and the Deevnet API page updated
