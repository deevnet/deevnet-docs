---
title: "CHG-0065: Removing a Tenant Leaves Nothing Behind"
weight: -65
---

# CHG-0065: Removing a Tenant Leaves Nothing Behind

| | |
|---|---|
| **Date** | 2026-11-12 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete.** API v0.21.0 deployed on `dv02prv001v01` and `deevnet-log-user` v0.21.0 on `dv02obs001v01`: a delete revokes the tenant's token and name, and purges its state, dashboards and log lines, proven on a throwaway tenant |
| **Window** | 2026-11-12, in an OpenBao work session. API deploys only; the log purge also restarts VictoriaLogs once for a new flag |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API, the state store); `dv02obs001v01` (the log store, its user writer, Grafana) |
| **Automation** | `deevnet-provisioning-api` (v0.20.0–v0.20.2; v0.21.0 for logs), `deevnet.mgmt` `site.yml --tags tenant-state`, `--tags deevnet-api`, and the `victorialogs` role. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium. Every new step deletes data. Most likely to go wrong: a purge reaching beyond the tenant it was asked for. Each one is held to the tenant's own prefix, organization or partitions, both in code and by the store's own permissions, and tested against a neighbor |
| **Related changes** | [CHG-0060](/docs/changes/2026/0060-state-secret-reissue/) |
| **Related incidents** | None |
| **Related runbooks** | [Tenant Removal](/docs/runbook/substrate/tenant-removal/) |

---

## Summary

A tenant delete removed everything the tenant could use, but not everything it left behind. Four
things outlived it:
- its Terraform state, every version;
- its log lines;
- the dashboards it saved;
- its API token, which could create the tenant again under the same name.

The token worked because a tenant token verifies without the registry, so that a tenant can restore
itself after the registry is lost ([ADR-0015 §5](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/#5-recovery-restores-the-index-or-issues-a-new-one)).
Once the delete removed the row, the token looked exactly like that restore.

This change makes the delete take all four with it. It closes both waypoints of the
[Tenant Removal](/docs/roadmap/infrastructure/tenant-services/tenant-removal/) roadmap item.

## Goal

- A deleted tenant's token is refused everywhere, including to create the tenant again. This holds
  for tenants deleted before the change too.
- The delete leaves no version of the tenant's state in the state bucket.
- The retired Grafana organization holds nothing the tenant made.
- The tenant's three log partitions are empty before its index can be given to another tenant.
- A name deleted and admitted again starts clean, with a new token that works.

## Scope

**In scope:** the API's tenant delete; the API's state-store permissions; the log store's delete API
and its user writer; `make remove-tenant`.

**Out of scope:**
- The audit log, which outlives tenants on purpose.
- The empty organizations Grafana keeps under `deleted-<name>-<id>`. Grafana 13 cannot delete an
  organization ([grafana/grafana#127386](https://github.com/grafana/grafana/issues/127386)).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The state purge reaches another tenant's state, or the fabric's | the state store | The API refuses any prefix that is not `tenants/<name>/`. Its store user may only list and delete under `tenants/*`, and cannot read anything. Tested against a neighbor and the fabric's state |
| The dashboards purge empties the wrong organization | Grafana | The organization is looked up by the tenant's name; organization 1 is refused outright |
| The log purge deletes another tenant's lines | the log store | Partitions are derived from the index at both ends, never sent. The writer refuses while any tenant's users name the index. Tested against VictoriaLogs v1.52.0 with a neighbor |
| The log store's delete API is reachable by a tenant | the log store | It listens on the store's loopback only, and vmauth routes nothing but `/select` and `/insert`. A test fails if a route ever reaches `/delete` |
| A legitimate restore is refused | the API | Only names that were deleted are refused, and only while unregistered. A restore after a lost registry is unaffected: the revocation records are lost with it |

## Prerequisites

- [x] OpenBao open (a work session) for every API deploy and live test
- [x] Vault decrypted; collections built
- [x] For the log purge: the API pull request and the `victorialogs` role pull request merged

## Procedure

| Step | What | Check |
|---|---|---|
| 1 | Token revocation: the delete records the token's hash; a revoked token is refused | Tests pass; live, the deleted tenant's token is 401 |
| 2 | The API's state-store user may purge under `tenants/*`; `site.yml --tags tenant-state` | The loaded policy lists the two S3 statements |
| 3 | State and dashboards purge; release, `make stage`, `site.yml --tags deevnet-api` | Live, a throwaway tenant's state and organization are empty after its own delete |
| 4 | Deleted names: tokens for any deleted name refused, seeded from the audit log | The table on the site holds every name the audit log saw deleted |
| 5 | Log purge: VictoriaLogs with `-delete.enable`, the writer's `purge`, the API step | Live, the throwaway tenant's three partitions are empty after its delete |
| 6 | The docs | Runbook, architecture page and roadmap match what a delete does |

**Rollback:** redeploy the previous API version. The revocation tables stay; an older API ignores
them. Purged data is gone, which is the point of the change.

## Verification

A throwaway tenant, `trm`, does what a tenant does:
- writes state, two versions and a lock;
- makes a folder with a dashboard in it, a dashboard at the top and an annotation;
- writes log lines, from step 5.

It then deletes itself with its own token. Afterwards:
- its old token is refused;
- its state prefix, organization and partitions are empty;
- admitted again, the name starts clean with a working new token.

## Outcome

**A delete now revokes the tenant's token and name, and takes its state, dashboards and log lines
with it.** Every step is deployed and proven on the site.

| Step | Result |
|---|---|
| 1 | API pull request 55; v0.20.0. Live: the old token is 401 reading or recreating its tenant, and an operator restore carrying it is 400 |
| 2 | `deevnet.mgmt` pull request 111 applied on `dv02prv001v01`; `deevnet-api-admin` lists `s3:ListBucket`, `s3:ListBucketVersions` on `tf-state` and `s3:DeleteObject`, `s3:DeleteObjectVersion` on `tf-state/tenants/*` |
| 3 | API pull requests 56 and 58; v0.20.1. Live on v0.20.1 and v0.20.2: `tf-state/tenants/trm/` went from 3 versions to none; the retired organization holds no folders, dashboards, annotations or library panels |
| 4 | API pull request 60; v0.20.2. The table holds `eds`, `tdemo`, `tprobe`, `tprobe2`, `trm`, `twk` and `wtest`. `trm`, on that list, was admitted again: new token 200, old token 401 |
| 5 | API pull request 62, v0.21.0; `deevnet.mgmt` pull request 115 applied on `dv02obs001v01`, which restarted VictoriaLogs once with `-delete.enable`. Live: `trm` (index 5) held 3 lines in each of `(5,0)`, `(5,1)` and `(5,2)`; after its own delete all three were empty and no delete task was left running. Lines written before the test in the partitions of `eds` and `mabell` were unchanged (123, 5805 and 207). Through the proxy, `trm`'s ingest and read tokens were both refused at `/delete` (`400`). No free index from 5 to 12 holds lines from an earlier delete |
| 6 | This record, the runbook, the architecture page, ADR-0015 §5 and the roadmap |

### Departures from the plan

- **The first live delete stopped at the dashboards step.** The site runs Grafana with alerting
  off ([ADR-0024 §3](/docs/architecture/decisions/platform-services/0024-dashboards/)). With
  alerting off, Grafana refuses to force-delete a folder's alert rules, even for the server admin,
  and the delete asked it to. The integration tests' Grafana ran with alerting on, so they passed.
  - Folders are now deleted plainly (v0.20.1).
  - The integration Grafana now runs with alerting off, and fails on the old code.
  - The stopped delete resumed cleanly once the folder was gone.
- **Revoking by hash did not reach tenants deleted earlier**, whose rows had kept no hash.
  - Deleted names were added, seeded from the audit log (v0.20.2).
  - Every name ever deleted is covered from the first start.
- **The retired organizations from earlier deletes were already empty.** There was nothing to clean
  in any of them.
- **The log purge uses VictoriaLogs' own delete, not a quarantine of the freed index.**
  - v1.52.0's source selects the tenant from the request's partition headers, one tenant per task.
  - Probed on data flushed to disk, a task removed exactly one tenant's lines, left no streams
    behind, and finished in seconds.

## To close

**What is left before this change closes, from its procedure and verification.**

- [x] Step 1: token revocation deployed and proven live
- [x] Step 2: the state-store policy applied
- [x] Step 3: state and dashboards purge deployed and proven live
- [x] Step 4: deleted names deployed; the table holds every deleted name
- [x] Step 5: the log purge merged, released (v0.21.0), the `victorialogs` role applied, deployed, and proven live
- [x] Step 6: the docs
