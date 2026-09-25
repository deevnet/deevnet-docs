---
title: "CHG-0024: Tenant Dashboards"
weight: 24
---

# CHG-0024: Tenant Dashboards

| | |
|---|---|
| **Date** | 2026-09-24 |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | **In progress.** Steps 1–4 are done and verified live: Grafana is on `obs`, the API is v0.8.0, and `tdemo`, `eds` and `mabell` have their organisations. The rebuild drill passed. Step 5 (the two `tenant_dev` rules) was applied by the operator on 2026-09-24: 68 rules, no drift. **Verification 3 from a `DVNTM-TD` laptop and from IoT remains.** See [Outcome](#outcome). |
| **Window** | 2026-09-24 14:52 to 15:03 EDT (steps 1–4 and the drill) |
| **Site** | mobile |
| **Systems** | `dv02obs001v01` (Grafana, beside the log store), `dv02prv001v01` (the API, v0.8.0), `dv02cor002p01` (two `tenant_dev` rules). Artifact mirror on `dv00bld001p01`. |
| **Automation** | `deevnet.builder` `site.yml --tags container-images,fetched-artifacts`; `deevnet.mgmt` `site.yml --tags dashboards` and `--tags deevnet-api`; `deevnet.net` `make migration-opnsense-firewall`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Grafana is new and nothing depends on it, and the API change adds one step after the log store's. Most likely to go wrong: the API deployed before Grafana, which fails every tenant's `dashboards` step until Grafana is up. The firewall apply has the usual guard ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)). |
| **Related changes** | [CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/) (the read token the data sources carry), [CHG-0022](/docs/changes/2026/0022-tenant-dev-network/) (the segment gaining two rules) |
| **Related incidents** | [INC-0004](/docs/incidents/) is open against the core router's `re0`. Don't apply the firewall while that NIC is misbehaving. |
| **Related runbooks** | [Dashboards](/docs/runbook/tenant/services/dashboards/), [Tenant Admission](/docs/runbook/substrate/tenant-admission/), [Take It Home on a Pi](/docs/runbook/tenant/take-it-home/) |

---

## Summary

Tenants can read their logs only by query. [ADR-0024](/docs/architecture/decisions/0024-dashboards/)
decided on Grafana OSS with one organisation per tenant, created by the API, and nothing was built.

The take-home Pi image needs dashboards before its first meetup. The Pi copies what Deevnet offers
rather than inventing its own, so Deevnet gets them first. That makes this change the contract the
Pi then reproduces: the organisation, the login, and three log data sources with **fixed UIDs**, so a
tenant's dashboard code applies unchanged to both.

There are no metrics yet. The dashboards read logs, and a numeric field in a device's JSON log line
can already be graphed.

## Goal

- Grafana 13.2.2 serves HTTPS on `dv02obs001v01:3000` with a site-CA certificate. The VictoriaLogs
  plugin 0.32.0 is loaded with a valid signature, and an unauthenticated request gets `401`.
- The API is v0.8.0. `tdemo`, `eds` and `mabell` each have an organisation, an Editor login in it
  and nowhere else, and the three data sources `deevnet-logs-workloads`, `deevnet-logs-platform` and
  `deevnet-logs-devices`.
- Logged in as `mabell`, `deevnet-logs-devices` shows the lines already in `(3, 2)`. The login
  cannot see another organisation or create a data source.
- From `DVNTM-TD`: `:8427` answers with a read token, and `:3000` loads. The router has 67 rules
  and no drift.

## Scope

**In scope:**
- the Grafana server
- the API step and the provider's attributes
- the two `tenant_dev` rules
- the tenant guide

**Out of scope:**
- metrics, and the metrics data sources (ADR-0023's change)
- substrate dashboards in organisation 1, since the store is tenants-only (ADR-0027)
- the Pi's Grafana, which is an image build and touches no substrate
- SSO

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| API deployed before Grafana | every reconcile | Deploy order: step 2 before step 3. A failed step names `dashboards`, leaves the tenant `provisioning`, and a reconcile after Grafana is up finishes it |
| A tenant named `admin` | the API | The client refuses the admin's name, and any login that is a server admin |
| A tenant login becoming Admin | Grafana | The API always sets `Editor`, and moves the login out of any other organisation, on every reconcile |
| Firewall apply | core router | The guarded apply of CHG-0007: plan first, apply, drift check |
| `obs` memory | `dv02obs001v01` (4 GB) | Grafana's minimum is 512 MB. 3.2 GB was free before the change |

## Prerequisites

- [x] `vault_grafana_admin_password` (`group_vars/all`) and `vault_grafana_secret_key`
  (`group_vars/observability_store`) vaulted, committed and **pushed**. Ciphertext was checked on
  origin (inventory `chg0024-dashboards`).
- [x] `grafana/grafana:13.2.2` and the plugin zip mirrored on the Builder:
  `deevnet.builder site.yml --limit dv00bld001p01 --tags container-images,fetched-artifacts`.
  The zip matched upstream's published sha1 and is pinned by sha256.
- [x] PRs merged: inventory #54, `deevnet.mgmt` #46 and #47, `deevnet.builder` #19, API #16, provider #8,
  image factory #9
- [x] Vault decrypted, collections built

## Procedure

### Step 1: Build and stage the API

**Run** (in `deevnet-provisioning-api`, on `main` after the merge):

```bash
git tag v0.8.0 && git push origin v0.8.0
make stage
```

**Verify:** `/srv/deevnet-http/container-images/deevnet-api/deevnet-api-v0.8.0.tar` exists.

**Undo:** nothing to undo; the running API is untouched.

### Step 2: Grafana on the observability store

**Run** (in `ansible-collection-deevnet.mgmt`):

```bash
ansible-playbook playbooks/site.yml --tags dashboards --limit dv02obs001v01
```

**Verify:**
1. The play's own checks pass: `/api/health`, an unauthenticated `/api/org` gets `401`, the admin
   password works, and the plugin reports version `0.32.0` with signature `valid`.
2. A second run reports `changed=0`.
3. `podman ps` on `obs` shows `grafana`, `victorialogs` and `vmauth` all up, and the log store is
   unaffected.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: The API

**Run:**

```bash
ansible-playbook playbooks/site.yml --tags deevnet-api --limit dv02prv001v01
```

**Verify:** the API reports `v0.8.0` and is ready. Its environment has `DEEVNET_GRAFANA_URL`.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: Give the existing tenants their organisations

Reconcile `tdemo`, `eds` and `mabell` with the operator token (`POST /v1/tenants/<t>/reconcile`).
Each response carries `dashboard.password`. Hand each one to its tenant as you handed over the log
tokens.

**Verify:** each tenant shows a `dashboards` step, `ok`, and `dashboard.org_id` ≥ 2. In Grafana
(*Administration → Organizations*) there are three tenant organisations, each with one Editor.

### Step 5: `tenant_dev` reaches the log store and Grafana

**Run** (in `ansible-collection-deevnet.net`):

```bash
make migration-opnsense-firewall                                  # plan: 2 to add, nothing else
make migration-opnsense-firewall EXTRA_ARGS="-e firewall_apply=true"
```

**Verify:** the plan shows exactly the two new rules. After the apply there are 67 managed rules and
no drift.

**Undo:** revert the two rules in `group_vars/all/firewall.yml` and apply again.

## Verification

1. **As `mabell`** (username and password from Step 4):
   - Explore on `deevnet-logs-devices` shows the `ma-bell-gw-01` lines already in `(3, 2)`.
   - `GET /api/user/orgs` lists one organisation, its own, as `Editor`.
   - `POST /api/datasources` gets `403`.
2. **Tenant Terraform from a `DVNTM-TD` laptop:** the
   [Dashboards](/docs/runbook/tenant/services/dashboards/) example applies a folder and the starter
   dashboard, and the next `terraform plan` is clean. This is also CHG-0022's untested
   `terraform plan` from that segment.
3. **From `DVNTM-TD`:** `curl` to `:8427` with a read token works, and `:3000` loads. **From IoT:**
   neither is reachable.
4. **Rebuild drill:** stop Grafana, move `/srv/grafana/data` aside, re-run Step 2, and reconcile.
   Organisations, logins with the same passwords, and data sources come back, and the tenant's
   apply restores its dashboards.
5. **Delete:** a throwaway tenant's login is gone, and its organisation is renamed
   `deleted-<tenant>-<id>` with no data sources (see below).

## Undo

### Undo Step 3

Pin `deevnet_api_version: "v0.7.0"`, remove `deevnet_api_grafana_url`'s value (set it to `""`),
and re-run `--tags deevnet-api`. Migration 0007 only adds columns, so v0.7.0 runs on the migrated
database. The tenants' organisations stay in Grafana until Step 2 is undone.

### Undo Step 2

`systemctl disable --now grafana` on `obs`, remove its firewalld port, and delete `/srv/grafana`.
The log store is untouched.

## Outcome

Live, 2026-09-24 (EDT):

| When | Step | What happened |
|---|---|---|
| 14:52 | 1 | API tagged `v0.8.0` and staged. The first `make stage` failed with the Builder's `/home` full (podman storage, the known 20 GB limit); dangling images were pruned and it passed. Provider tagged `v0.4.0` |
| 14:54 | 2 | Grafana deployed. **The plugin check failed**: see the first departure below. Fixed in mgmt #47 and redeployed. The plugin loads at 0.32.0 with signature `valid`, an unauthenticated `/api/org` gets `401`, and a second run is `changed=0` |
| 14:58 | 3 | API v0.8.0 deployed, and the role confirmed the running version |
| 15:00 | 4 | `tdemo`, `eds` and `mabell` reconciled: all `ready`, with a `dashboards` step and organisations 2, 3 and 4 |
| 15:01 | Verification 1 | As each tenant: one organisation, its own, as `Editor`. The three UIDs answer. `POST /api/datasources` gets `403`. Through Grafana, `mabell` reads its 4 device lines from CHG-0021, including the `liar-…` line filed under `mabell`, and `eds` reads its own line |
| 15:02 | Verification 2 | The Dashboards page's Terraform, as `tdemo` from the Builder (not from `DVNTM-TD`, whose rules wait on step 5): applied, the next plan was clean, then destroyed |
| 15:03 | Verification 4 | Rebuild drill: Grafana stopped, its data moved to `/srv/grafana/data.drill-20260924`, the role re-run and the tenants reconciled. The organisations came back as 2, 3 and 4 with **the same passwords**, and the data sources and the log reads work again |
| — | 5 | The plan showed exactly the two new rules, with none to delete. The automated session's permission classifier refused the apply |
| later | 5 | **Applied by the operator**, together with CHG-0025's rule. The re-plan shows 0 to add and 68 rules present, with no drift |
| 19:59 | Verification 3 | From a laptop on `DVNTM-TD` (lease `10.20.45.51`): `segment-check.sh DVNTM-TD` **29/29**. The log store `:8427` and Grafana `:3000` are reachable over verified TLS; everything else on the site is still blocked, including SSH to `obs`. `tenant-check.sh` passed every check. From `DVNTM-IOT`: **12/12**, but that profile did not yet try `obs`'s ports; the checks were added in net #37 and need one more IoT run |

What was done, and tested off the site:

| When | What | Result |
|---|---|---|
| 2026-09-24 | Secrets | Generated on the Builder, vaulted by the operator, committed and pushed; ciphertext checked on origin |
| 2026-09-24 | Mirror | `grafana-13.2.2.tar` (1.4 GB) and the plugin zip on the Builder |
| 2026-09-24 | API | `make test-integration` passes against throwaway PostgreSQL, PowerDNS, MinIO and **Grafana 13.2.2** containers. The Grafana test creates a tenant, checks the Editor can't create a data source (`403`), repairs a drifted password and a membership in organisation 1, and removes the tenant twice |
| 2026-09-24 | End to end, off the site | VictoriaLogs v1.52.0 and vmauth v1.152.0, configured by the real `deevnet-log-user` renderer, plus Grafana 13.2.2, in one pod. The API's client created the tenant. As the tenant's login, `deevnet-logs-workloads` returned only the `(7,0)` line, `deevnet-logs-devices` only the `(7,2)` line, and `deevnet-logs-platform` nothing. The partition header and the CA pass through the plugin |
| 2026-09-24 | Tenant Terraform, off the site | `grafana` provider v4.46.0: the example applied, and the next plan was clean |
| 2026-09-24 | The role's mechanics, off the site | The plugin unpacked with Python's `zipfile` and the role's `chmod`s loads with signature `valid`. The role's full `GF_*` set starts with no errors. `grafana cli admin reset-admin-password` resets the admin |
| 2026-09-24 | Pi image | Built from local inputs and booted under nspawn and qemu: all six services active, the same data sources and UIDs, a `temp_c` series graphed, and the Terraform applied from the card's `kit.env` |

### Departures from the plan, and what was found

- **The role's plugin marker broke the plugin's signature.** The role recorded the unpacked version
  in a file **inside** the plugin's directory. Grafana checks that directory against the plugin's
  signed manifest, so an extra file makes the signature "modified" and the plugin refuses to load.
  The off-site test had unpacked the plugin without the marker, so it passed. The marker now sits
  beside the plugins directory (mgmt #47).
- **Verification 3 (from `DVNTM-TD` and IoT) and 5 (deleting a throwaway tenant) were not run live.**
  Verification 3 needs step 5. The delete path is covered by the API's integration test against
  Grafana 13.2.2.

- **Grafana 13 ignores `OrgId` on user create when `users.auto_assign_org` is off.** It then makes
  every new user a personal organisation named for its login, which is the tenant's own name. With
  it on (the default), the named organisation wins and the login lands only there, as Viewer, before
  the API sets Editor. So ADR-0024 §3's *"new users are not added to the main organisation"* holds
  through the API naming the organisation, not through that setting.
- **Grafana 13 cannot delete an organisation.** `DELETE /api/orgs/<id>` answers `500` on every 12.x
  and 13.x release with unified storage ([grafana/grafana#127386](https://github.com/grafana/grafana/issues/127386);
  the fix, #127404, is unmerged). A tenant delete removes the data sources and the login, tries the
  delete, and on a `500` renames the organisation `deleted-<tenant>-<id>`, which frees the name. When
  the fix ships, the delete succeeds and nothing needs changing.
- **The `grafana` provider ignores provider-level `org_id` under basic auth.** It sends organisation
  1, where the tenant is not a member, and gets `403`. Every resource must carry `org_id`, so the
  contract adds `TF_VAR_grafana_org_id`.
- **Grafana 13 tries to download plugins at start.** `GF_PLUGINS_PREINSTALL_DISABLED`, the update
  checks and the news feed are off, since `obs` has no internet.
- **Port 3000, not 443.** The image runs as an unprivileged uid.
- **The tenant guide's ingest example stored nothing.** Reproduced on the site's VictoriaLogs
  version: a jsonline POST without `Content-Type: application/stream+json` answers `200` and keeps
  nothing. The [Logs](/docs/runbook/tenant/services/logs/) page is fixed.
- **The API's store tests had not run cleanly since CHG-0016.** Their reset never dropped
  `tenant_broker_accounts`. That hid a step count left stale by CHG-0020. Both are fixed.

## Follow-ups

- [x] Step 5 (`tenant_dev` rules), applied by the operator
- [x] Verification 3 from `DVNTM-TD`: 29/29
- [ ] Verification 3 from IoT: re-run `segment-check.sh DVNTM-IOT` (net #37 added the `obs` checks)
- [ ] Hand `tdemo`, `eds` and `mabell` their dashboard passwords (in the operator's reconcile
      output of 2026-09-24)
- [ ] Remove `/srv/grafana/data.drill-20260924` on `obs` once no one needs it
- [ ] When grafana/grafana#127404 ships: upgrade, and delete the `deleted-*` organisations
- [ ] ADR-0024 → Accepted once this is Complete
