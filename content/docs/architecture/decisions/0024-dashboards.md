---
title: "ADR-0024: Dashboards"
weight: 24
---

# ADR-0024: Dashboards Are Grafana, One Organisation per Tenant, Declared as Code

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-21 |
| **Scope** | How the operator and each tenant view their metrics and logs as dashboards, how people log in to do it, how dashboards are declared as code, and what a tenant may and may not configure. Not alerting, which ADR-0023 decides. |
| **Extends** | [ADR-0023: Metrics and Alerting](/docs/architecture/decisions/0023-metrics-and-alerting/), whose §5 deferred saved dashboards and named Grafana with one organisation per tenant as the likely shape |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) §4, [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/) §4, §7, [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/0016-substrate-secrets-openbao/), [ADR-0022: Central Logging](/docs/architecture/decisions/0022-central-logging/) |

---

## Context

### What exists to read data

ADR-0022 and ADR-0023 store logs and metrics, partitioned per tenant behind vmauth. The only reading
surfaces they give are the store's own UIs:
- **vmui** loads *predefined* dashboards from JSON files set by the operator. It has no per-user or
  per-tenant dashboard storage.
- **VictoriaLogs' built-in UI** is a *"Web UI for logs querying and exploration"*, with no
  dashboards.

Both are fine for the operator exploring. Neither lets a tenant keep dashboards of its own.

### What is wanted

1. **The operator sees every partition** and keeps substrate dashboards.
2. **A tenant sees only its own partitions and its own dashboards.**
3. **Dashboards are code.** The substrate declares its dashboards in its automation, and a tenant
   declares its own in its Terraform.
4. **People log in.** There is no identity directory yet. ADR-0013 lists one for the identity VM
   as *"later"*.
5. **It installs offline.** Nothing may be fetched from the internet at runtime.

---

## Options considered

Vendor documentation was checked on 2026-09-21.

| | Grafana OSS | Perses | vmui and the VictoriaLogs UI only |
|---|---|---|---|
| **License** | AGPLv3 | Apache 2.0 | Apache 2.0 |
| **Tenant boundary** | organisations | projects, with roles per project | none |
| **Tenant manages dashboards in Terraform** | yes, the `grafana/grafana` provider | no provider found | no |
| **Maturity** | long-established | CNCF sandbox, pre-1.0 (v0.54.0) | — |
| **Logs and metrics** | built-in Prometheus data source; a VictoriaLogs plugin (Apache 2.0) | `prometheus` and `victorialogs` plugins | built in |

### A — Grafana OSS, one organisation per tenant *(chosen)*

- **An organisation is a real boundary:** *"The member of one organization cannot view dashboards
  assigned to another organization."* A user can be in several, so the operator can be in all of
  them.
- **Inside an organisation there is no data-source boundary.** Data-source permissions are
  *"Available in Grafana Enterprise and Grafana Cloud"*. In OSS, *"data sources in an organization
  can be queried by any user in that organization."* That is why the organisation, not the data
  source, is the tenant boundary.
- **A Terraform provider exists.** `grafana/grafana` takes an `org_id` and `auth` as a token or
  `username:password`. Its `grafana_folder` and `grafana_dashboard` resources work inside one
  organisation.
- **Against:**
  - AGPLv3. Running it unmodified inside the site creates no obligation.
  - Organisations must be created with server-admin basic auth. *"You can't authenticate to the
    Admin Organizations HTTP API with service account tokens."*

### B — Perses

- **For:**
  - Apache 2.0.
  - A project model with per-project roles.
  - Dashboards-as-code through its CUE and Go SDKs.
  - A VictoriaLogs plugin.
- **Against:**
  - No Terraform provider, so a tenant would declare dashboards with `percli` outside Terraform.
    That breaks requirement 3 as the site does it.
  - It is a *"sandbox project"* and pre-1.0.
- **Verdict:** Not now. See *What would reopen this*.

### C — The stores' own UIs only

- **For:** nothing new to run.
- **Against:** no per-tenant dashboards, and no dashboards as code for tenants.
- **Verdict:** Rejected as the tenant surface. They stay the operator's exploration tools.

---

## Decision

**Option A: Grafana OSS on `dv02tob001v01`.** Each tenant gets one organisation, which the API
creates. The substrate owns the data sources, and a tenant owns only its folders and dashboards.

### 1. Placement

- **Grafana runs as a container on `dv02tob001v01`**, beside the stores it reads, and is reachable
  over HTTPS from the same zones as vmauth.
- **Its database is SQLite, on the data disk, treated as rebuildable** (§6). Grafana's advice that
  *"SQLite isn't recommended for production environments"* is noted. Nothing in this database is
  meant to be authoritative.

### 2. One organisation per tenant, built by the API

When the API creates a tenant (ADR-0015), it also creates:
- **an organisation** named for the tenant
- **four data sources in it**, each carrying the tenant's ADR-0022 read token as a bearer header in
  Grafana's encrypted `secureJsonData`:
  - metrics `(index, 0)` and `(index, 1)`, using Grafana's built-in Prometheus data source against
    `/select/<index>:<project>/prometheus`
  - logs `(index, 0)` and `(index, 1)`, using the VictoriaLogs plugin
- **one Grafana login for the tenant**, with the Editor role in that organisation only

Further details:
- **The API holds Grafana's server-admin credential in OpenBao KV**, beside its other backend
  credentials (ADR-0016). It reaches Grafana on Platform directly, with no new zone rule.
- **The built-in Prometheus data source is used for metrics**, not VictoriaMetrics' own plugin.
  VictoriaMetrics says *"most users can use Prometheus datasource for Grafana"*. Its plugin is
  AGPL-3.0 and pinned to narrow Grafana version ranges. What is given up is some MetricsQL-specific
  editor support.
- **The VictoriaLogs plugin is required for logs.** It is Apache 2.0 and is installed from a zip
  mirrored on the artifact server, because Grafana can install *"by extracting the archive into the
  plugin directory"*.

### 3. A tenant is an Editor, never an Admin, of its own organisation

**This is the central restriction.** An organisation Admin can create data sources, and a data source
is a URL that Grafana's server requests on the user's behalf. A tenant able to create one could:
- point Grafana at any address `tob` can reach: the API, OpenBao and tenant DNS on Platform, and
  the internet
- or swap its own read token for another value

That is the same concern that kept tenant webhooks out of ADR-0023.

So:
- **A tenant's login is Editor.** It can create folders and dashboards, and it can't create or
  change data sources.
- **The four data sources are the substrate's**, created and repaired by the API.
- **Grafana's own alerting is turned off.** Alerting is ADR-0023's, and Grafana's contact points
  would re-open the webhook question.
- **Anonymous access stays off**, and new users are not added to the main organisation.

### 4. The operator

- **Organisation 1 is the operator's and holds no tenant data.** Its data sources use the
  operator's read token, including `/select/multitenant/` for metrics.
- **Substrate dashboards are provisioned from files by Ansible** into organisation 1. That is
  Grafana's file provisioning with `orgId`.
- **The operator is a server admin**, able to enter any tenant's organisation to help debug.
  Entering is visible to the tenant as a member.

### 5. Login and dashboards as code

- **One credential per tenant: its Grafana login**, a username and a password. The API issues it at
  tenant creation, returns it in the create response, and keeps it restorable from tenant state, as
  every other tenant credential (ADR-0012 §4).
- **The tenant's Terraform uses the same login.** The `grafana/grafana` provider takes basic auth
  as `username:password`, with `org_id` set to the tenant's organisation. The tenant manages
  `grafana_folder` and `grafana_dashboard`, and its Editor role prevents it managing
  `grafana_data_source`.
- **The provider comes from the site's offline mirror** (ADR-0012 §7), fetched with `terraform
  providers mirror` like every other third-party provider.
- **Why a login rather than a service-account token:** Grafana generates a service-account token
  itself, so after a rebuild that token can't be restored from tenant state. It would have to be
  reissued. A password can be set back to the value the tenant holds, which is the resupply pattern
  ADR-0015's tenants already use.
- **When the identity VM gets a directory,** human login moves to OIDC or LDAP, and the password
  becomes automation-only.

### 6. Dashboards are re-derivable; clicks are not

- **What survives a Grafana rebuild:**
  - organisations, logins and data sources, which the API recreates on reconcile
  - tenant dashboards, which the tenant's next apply recreates
  - substrate dashboards, which Ansible re-provisions
- **What doesn't: a dashboard built only in the UI.** That is stated plainly to tenants, as ADR-0010
  §4 requires: tenant content must be re-derivable from the tenant's code. A dashboard built by
  clicking should be exported into the tenant's repository.
- **So Grafana's database gets no off-host copy.**

---

## Consequences

**Tenants get dashboards, and they are theirs to declare.** A tenant manages its dashboards in the
same Terraform it uses for everything else, through a provider it didn't have to learn from Deevnet.

**The substrate owns every data source.** A tenant can't choose what Grafana reads or where it
connects. The price is that a tenant can't add a data source of its own, such as its own database,
in v1.

**A tenant holds a third observability credential.** It now has ADR-0022's ingest and read tokens
and a Grafana login.

**The API grows again.** It gains a Grafana backend: organisations, users and data sources, with
reconcile and resupply like the others.

**`tob` gets heavier.** Grafana's documented minimum is *"512 MB"* and *"1 core"*, on top of what
ADR-0023 already lists.

**Grafana's version is constrained by the VictoriaLogs plugin's**, which needs *"Grafana
>=10.4.0"*. A Grafana upgrade needs a plugin compatibility check.

---

## Open questions

1. **Should a tenant have two logins,** one for people and one for its Terraform? It would separate
   rotation and audit at the cost of another credential.
2. **Should a tenant be able to share a dashboard with another tenant?** Organisations don't share.
   A copy through code is the answer today.
3. **PostgreSQL instead of SQLite**, if Grafana's own state ever becomes more than rebuildable.
4. **Should the operator's presence in a tenant's organisation be announced?** For example, an event
   published to the tenant's `(index, 1)` log partition when the operator enters.

## What would reopen this

- **Perses reaching 1.0 with a Terraform provider.** It is Apache-licensed and project-scoped, which
  fits this model without the organisation workaround.
- **Needing data-source permissions inside one organisation**, for example several teams per tenant.
  That is an Enterprise feature, so it would be a licence decision.

## To confirm when building

- That an Editor in Grafana OSS can't create, edit, or read the secure fields of data sources, and
  can't create alerting contact points once unified alerting is off.
- That the `grafana/grafana` provider, with basic auth and `org_id`, manages folders and dashboards
  in that organisation for a non-admin member, and is refused elsewhere.
- That the VictoriaLogs plugin's catalog build is signed, so no unsigned-plugin exception is needed,
  and that it installs from a local zip with no internet.
- That the built-in Prometheus data source queries `/select/<index>:<project>/prometheus` through
  vmauth with a bearer header.

---

## Current state

- **Proposed. Nothing is built.**
- No Grafana runs anywhere.
- The stores in ADR-0022 and ADR-0023 are not built either.
