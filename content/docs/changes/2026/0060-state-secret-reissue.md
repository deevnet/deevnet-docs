---
title: "CHG-0060: An Operator Reissue of a Tenant's State Secret"
weight: -60
---

# CHG-0060: An Operator Reissue of a Tenant's State Secret

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | Planned. The API route, its tests and the operator target are written; not released or deployed |
| **Window** | Unscheduled. One API deploy; no tenant's secret changes until the operator asks for it |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API); the state store on the same VM |
| **Automation** | `deevnet-provisioning-api` (tag and stage), `deevnet.mgmt` `site.yml --tags deevnet-api`, `make reissue-state-secret` |
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
| 3 | `make reissue-state-secret NAME=tdemo` | The handover file is 0600 and holds the new secret; tdemo's old `.backend.env` is refused and the new one gives a clean `terraform plan` |
| 4 | The docs | *Lost State or Credentials* gives the reissue as the way back; the API's page lists the route |

**Rollback:** redeploy the previous API version. A secret already reissued stays in force: it is in
the registry, and the previous version reconciles with what the registry holds.

## Verification

An operator gives tdemo a new state secret, and tdemo reads its state with it and not with the old one.

## To close

**What is left before this change closes, from its procedure and verification.**

- [ ] Step 1: the API route and the operator target merged, tests passing
- [ ] Step 2: the API released and deployed; every tenant reconciles `ok`
- [ ] Step 3: tdemo reissued; the old secret refused, the new one plans clean
- [ ] Step 4: *Lost State or Credentials* and the Deevnet API page updated
