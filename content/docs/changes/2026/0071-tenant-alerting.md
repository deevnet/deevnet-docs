---
title: "CHG-0071: Tenant Alerting"
weight: -71
---

# CHG-0071: Tenant Alerting

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | **Complete** (2026-11-15). Tenants' alert rules run on `obs`, and the verification passes on site, as two tenants, with an Android phone (27 of 27). Step B of [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) |
| **Window** | None needed: the new services start beside the running ones, vmauth is unchanged, and the API redeploy is a restart of a few seconds |
| **Site** | mobile |
| **Systems** | `dv02obs001v01` (vmalert per tenant, Alertmanager, ntfy), `dv02prv001v01` (the Deevnet API), `deevnet-tenant-tdemo` |
| **Automation** | `deevnet.mgmt` `site.yml --tags alerting,log-store,service-proxy,deevnet-api --limit` the host; `deevnet-provisioning-api` and `terraform-provider-deevnet` releases and `make stage`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Most likely to go wrong: a rule that labels its way into another tenant's topic, caught by the API and the writer refusing the label, and tried by the verification |
| **Related changes** | [CHG-0070](/docs/changes/2026/0070-tenant-metrics-store/) (the store the rules read), [CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/) (the read token each tenant's vmalert holds), [CHG-0046](/docs/changes/2026/0046-service-proxy/) (443 by name) |
| **Related runbooks** | [Alerting](/docs/runbook/tenant/services/alerting/) |

---

## Summary

Tenants can push and query metrics and logs, but nothing tells them when something is wrong.
[ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) §5 adds
alerting. This change builds it:
- **A tenant declares rule groups in Terraform**, `deevnet_alert_rule_group`, each over its metrics
  or its logs.
- **Each tenant's rules run in its own vmalert on `obs`**, with its own read token, so a rule can
  read only what the tenant can read.
- **One Alertmanager sends each alert to the tenant's ntfy topic**, `<tenant>-<topic>`, and the
  tenant's phone, on site, subscribes with a login the API issues.

## Goal

- A tenant's rule over its metrics, and one over its logs, each fire and reach an Android phone on
  site, and each sends a resolved notification when it clears.
- A rule that sets the `tenant` label, or a recording rule, is refused by the API.
- A rule that queries another tenant's data reads only its own.
- A tenant's ntfy login reads only `<tenant>-*`, and publishes nowhere.
- Removing a tenant removes its rules, its vmalert and its ntfy login.

## Scope

**In scope:**
- On `obs`, each on loopback, behind the service proxy where a phone needs it:
  - **vmalert**, one instance per tenant with rules, started and stopped as the tenant's rules
    come and go; the binary from its image, run by systemd;
  - **Alertmanager**, one, in a container, with a route per tenant and topic;
  - **ntfy**, in a container, at `ntfy` on 443, with `auth-default-access: deny-all`.
- **The writer** (`deevnet-log-user`) gains each tenant's rule files, its vmalert settings, its ntfy
  login and its Alertmanager routes. It stays unprivileged: a root systemd path unit on `obs`
  starts and stops each tenant's vmalert when its files change, and restarts ntfy when its users
  change.
- **The API:** rule groups under `/v1/tenants/{name}/alert-rule-groups`, validated; the tenant's
  ntfy login and `notify_endpoint`; reconcile and removal covering both.
- **The provider:** `deevnet_alert_rule_group`, and `notify_endpoint`, `notify_username` and
  `notify_password` on `deevnet_tenant`.
- **The tenant docs**, an Alerting page, and a tdemo example.

**Out of scope:**
- iOS. Without forwarding poll requests to ntfy.sh, its delivery *"can take hours"* (Step 1), and a
  private CA on iOS is not documented. It stays with off-site delivery (ADR-0023 Open question 2).
- Recording rules, webhooks and email (ADR-0023 §5).
- Alerts for the substrate.
- Each workload's resource use (step C).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A rule sets `tenant` and routes to another tenant's topic | vmalert, Alertmanager | vmalert lets a rule's labels beat `-external.label` (Step 1, finding 1), so the API refuses the label and the writer refuses it again before writing; verification tries it |
| A rule reads another tenant's data | vmalert | It queries with the tenant's own read token, through vmauth; verification tries naming another partition and the multitenant paths |
| A tenant's phone reads another tenant's alerts | ntfy | Its login may read `<tenant>-*` only; verification subscribes to another tenant's topic and is refused |
| Many tenants' vmalerts crowd out the stores | `obs` | Each capped in memory; measured in Step 2 |
| A wrong Alertmanager configuration stops every tenant's alerts | Alertmanager | The writer renders it from validated groups only, and Alertmanager refuses a reload it can't load, keeping the configuration it runs |

## Prerequisites

- [x] ADR-0023 §5 revised for this change: the rule resource, the label guard, Android first
- [x] The current releases, flags and paths checked against the vendor documentation (Step 1)

## Procedure

### Step 1: Check the vendor claims

Recorded under Outcome.

### Step 2: Prove it off site

vmalert, Alertmanager and ntfy in containers on the Builder, beside the store and vmauth, with two
tenants' files rendered by the writer. Run the verification's refusals there first, with ntfy's
CLI as the subscriber. Measure each component's memory. Confirm what Step 1 leaves open:
- one vmalert evaluates a metrics group and a logs group through vmauth;
- a group's partition header reaches the device partition and no other tenant's;
- ntfy picks up changed users without losing its messages.

### Step 3: The inventory

- The `ntfy` alias, and an `ntfy` entry in `service_proxy_vhosts`, with WebSockets.
- The three images in `artifact_servers.yml`, pinned.

### Step 4: The alerting role

A `deevnet.mgmt` role, tagged `alerting`:
- Alertmanager and ntfy as containers on `obs`, on loopback, with data on the data disk;
- a `vmalert@.service` template, one instance per tenant, reading the tenant's directory, with
  `-external.label=tenant=<name>` and no `-remoteWrite.url`;
- the root path unit that starts, stops and restarts them when the writer's files change.

### Step 5: The API

- **Rule groups:** create, read, update and delete under `/v1/tenants/{name}/alert-rule-groups`.
  The API refuses a recording rule, a `tenant` label or annotation key, a topic that is not a plain
  name, and an interval under 30 seconds. It caps the rules per tenant.
- **The ntfy login:** issued with the tenant's other secrets; the writer receives only its hash.
- **The writer:** rule files, vmalert settings, ntfy users and Alertmanager's routes. Purge removes
  all of them.
- **The tenant's response** gains `notify_endpoint`, `notify_username` and `notify_password`.
- Reconcile applies all of it to existing tenants. Release, with the CHANGELOG.

### Step 6: The provider

`deevnet_alert_rule_group`, and the three `notify_*` attributes on `deevnet_tenant`. Release, with
the CHANGELOG and the docs site, and stage it in tenant downloads.

### Step 7: Deploy

1. The alerting role.
2. The log store role: the new writer.
3. The service proxy, for `ntfy`.
4. The API, then reconcile tdemo, eds and mabell.

### Step 8: Docs and the reference tenant

- **The tenant runbook:** an Alerting page (rules, topics, the phone, Android only for now), and
  Coming Soon without alerting.
- **`deevnet-tenant-tdemo`:** a rule group over its metrics and one over its device logs.
- **Platform docs:** the Deevnet API's and the provider's pages, and the Software Catalog.

## Verification

On site, as two tenants, with an Android phone subscribed:
- A rule over metrics fires, reaches the phone, and sends a resolved notification when it clears.
- A rule over device logs does the same.
- A rule with a `tenant` label, and a recording rule, are refused by the API.
- A rule querying another tenant's partition, or the multitenant paths, reads only its own data or
  nothing.
- Each tenant's ntfy login is refused the other's topics, and refused a publish.
- Removing a test rule group stops its tenant's vmalert when it was the last.
- Each tenant still writes and reads its metrics and logs.

## Undo

### Undo Step 7

Redeploy the previous API release and writer; stop the alerting role's containers and units. The
tenants' rule groups stay in the API's registry for the next attempt.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the vendor claims checked and recorded
- [x] Step 2: proven off site, refusals included
- [x] Step 3: the inventory changes merged
- [x] Step 4: the alerting role merged
- [x] Step 5: the API released
- [x] Step 6: the provider released and staged
- [x] Step 7: deployed; tdemo, eds and mabell reconciled
- [x] Step 8: the Alerting page, Coming Soon updated, the tdemo example
- [x] Verification passes on site with an Android phone

## Outcome

### Step 1: the vendor claims (2026-11-14)

Checked against the vendors' documentation and release pages, and vmalert's source where the
documentation was unclear.

| Claim | Found | Holds |
|---|---|---|
| Current releases | vmalert `v1.156.0` (vmutils, 2026-11-09), the store's release; Alertmanager `v0.35.0` (2026-11-09), `quay.io/prometheus/alertmanager`; ntfy `v2.38.0` (2026-11-14), `binwiederhier/ntfy` | Yes |
| One vmalert for metrics and logs | *"We recommend running separate instances of vmalert for VictoriaMetrics and VictoriaLogs. However, vmalert supports having many groups with different rule types"*, with one `-datasource.url` and vmauth routing. Log rules query `/select/logsql/stats_query` and `stats_query_range` | Yes, against the vendor's recommendation. Step 2 proves it; if it fails, each tenant runs two |
| The read token as the datasource's credential | `-datasource.bearerToken` and `-datasource.bearerTokenFile` | Yes |
| A group can choose a partition | A group's `headers` are *"applied for all rules requests within a group"* and *"have priority over headers set via `-datasource.headers`"* | Yes. vmauth overwrites `AccountID` and `ProjectID` on every route, so a header can only choose among the tenant's own partitions |
| Alerts only | *"For recording rules to work `-remoteWrite.url` must be specified"*; without it vmalert refuses a rule file holding one | Yes, a second guard behind the API's. Alert state is then held in memory only |
| Rules reload in place | `SIGHUP`, `/-/reload`, `-configCheckInterval`; `-dryRun` checks files only | Yes |
| Multi-tenancy in vmalert | `-clusterMode` *"is available only in Enterprise binaries"* | As ADR-0023 assumed: one instance per tenant |
| Alertmanager to ntfy | `webhook_configs` with `http_config.authorization` (bearer); reload by `SIGHUP` or `POST /-/reload`; `amtool check-config` | Yes. Alertmanager has no multi-tenancy |
| ntfy's per-tenant access | `ntfy access USERNAME TOPIC PERMISSION`, with *"a wildcard pattern… (e.g. `alerts_*` or `ben-*`)"*; `auth-users` and `auth-access` in the configuration since `v2.14.0`, with password hashes | Yes |
| ntfy formats Alertmanager's payload | *"the query parameter `?template=...`"*, with a pre-defined `alertmanager` template, since `v2.14.0` | Yes |
| Behind the service proxy | *"you must set the `behind-proxy` flag"*, and *"Be sure to enable WebSockets"* | Yes |
| Messages survive a restart | In memory for 12 hours by default; `cache-file` keeps them on disk | Yes, with `cache-file` |

**Finding 1: a rule's own labels beat vmalert's `-external.label`.** Group `labels` *"have priority
over the external labels"*, and a rule's `labels` *"add or overwrite labels from other external
label sources"*. No flag stops it. So the `tenant` label Alertmanager routes on is not safe from a
rule on its own. **The API refuses a `tenant` label, and the writer refuses it again before it
writes a file.** Tenants have no other way to write a rule file, so that check is the boundary. A
`tenant` label on a tenant's own series is not a risk: on a conflict with an external label,
*"original labels are kept with prefix 'exported_'"*.

**Finding 2: iOS waits for ntfy.sh.** For instant delivery, ntfy must *"forward so called
`poll_request` messages to the main ntfy.sh server"* with `upstream-base-url`, and without it
*"delivery can take hours"*. The forward carries a message ID and a hash of the topic URL, not the
message. Importing a server certificate is documented for Android only. **This change proves
Android only**, on site, with nothing sent off site; iOS stays with ADR-0023's Open question 2.

**Finding 3: ntfy's declared users are the whole list.** *"Removing users from the config file will
delete them from the database"*, and users made by hand become declared ones. **The writer is the
only thing that manages ntfy's users**, through `auth-users` and `auth-access`, and nothing adds one
by hand.

### Step 2: proven on the Builder (2026-11-15)

vmalert `v1.156.0` for two tenants, Alertmanager `v0.35.0` and ntfy `v2.38.0` in containers on the
Builder, beside the step A store, VictoriaLogs and vmauth with step A's two tenants, tdemo (index 1)
and eds (index 2). The rule files, routes and ntfy users were written by hand in the shape the
writer will write them, with ntfy's own client API standing in for the phone.

**The whole path works.**
- eds's metrics rule fired and reached `eds-backend`. When the value dropped, *"✅ Resolved"*
  followed.
- eds's rule over its device logs, a `vlogs` group with the partition header `2-2`, fired and
  reached `eds-devices`.
- **One vmalert runs both rule types** through vmauth, against the vendor's recommendation: one
  instance per tenant is enough.

**A rule can't read another tenant's data.** tdemo ran three rules aimed at eds:
- a query for eds's metric;
- the same query with eds's partition header and `AccountID: 2`;
- a log rule with eds's device partition header and `AccountID`/`ProjectID`.

None saw eds's data. Each did fire once tdemo wrote the same data into its own partitions, with
tdemo's own values (`app="mine"`, 7), and reached `tdemo-backend`. The queries work; they read only
tdemo's partitions.

**The `tenant` label is the hole Finding 1 said.** tdemo's rule labeled `tenant: eds` reached
`eds-backend`, and vmalert logged it: *"label "tenant"="tdemo" for rule "spoof"."SpoofTenant"
overwritten with external label "tenant"="eds"*. Nothing on `obs` stops it, so the API's refusal and
the writer's are what does.

**ntfy refuses what it should:**
- tdemo reading `eds-backend`, eds reading `tdemo-backend`, and anyone without a login (403);
- a tenant publishing, even to its own topic, and the publisher reading (403);
- a wrong password (401);
- eds reading the bare topic `eds`, outside its `eds-*` (403).

A tenant's own topics under its prefix are open to it. `eds-*` cannot match another tenant's topics
because tenant names have no hyphen (`^[a-z][a-z0-9]{0,7}$`).

**The writer's mechanics hold:**
- ntfy, restarted with tdemo's user removed and mabell's added, kept every message (`cache-file`).
  tdemo's login then failed (401), and mabell's read only `mabell-*`.
- `amtool check-config` passes the generated routes and refuses a configuration naming a receiver
  that doesn't exist. Alertmanager reloads on `POST /-/reload`.
- vmalert refuses to start on a recording rule without `-remoteWrite.url`: *"config contains
  recording rules but `-remoteWrite.url` isn't set"*. `-dryRun` refuses a rule that doesn't parse.
- A running vmalert picks up a changed rule file on `SIGHUP`, keeping its other groups running.
  Each tenant's vmalert is reloaded, not restarted, when its rules change.

**Memory:** each tenant's vmalert used 5 to 8 MB, Alertmanager 15 MB and ntfy 15 MB. `obs` has about
3 GB available.

### Steps 3 to 7: released and deployed (2026-11-15)

- **Merged and released:**
  - the inventory ([ansible-inventory-deevnet#116](https://github.com/deevnet/ansible-inventory-deevnet/pull/116));
  - the alerting role and the writer's settings ([ansible-collection-deevnet.mgmt#134](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/134));
  - the API and writer `v0.25.0` ([deevnet-provisioning-api#76](https://github.com/deevnet/deevnet-provisioning-api/pull/76), [#77](https://github.com/deevnet/deevnet-provisioning-api/pull/77));
  - the provider `v0.13.0` ([terraform-provider-deevnet#38](https://github.com/deevnet/terraform-provider-deevnet/pull/38), [#39](https://github.com/deevnet/terraform-provider-deevnet/pull/39)).
- **What changed from the plan:**
  - **vmalert runs as a binary, not a container.** The binary is copied out of the pinned image
    and run by systemd as `vmalert@<tenant>`, as its own user.
  - **No `amtool`.** The writer reloads Alertmanager over loopback; Alertmanager refuses a reload it
    can't load, and keeps running the configuration it has.
  - **`-dryRun` checks expressions, not annotation templates.** A template error shows only when
    the alert is sent.
- **DNS:** `ntfy.mobile.deevnet.net` resolves to `obs`, and the router's configuration was backed up
  after.
- **`obs` and `prv`:** the alerting role, the writer, the service proxy and the API ran with no
  failure. Alertmanager and ntfy answer their health checks, and the API runs `v0.25.0` with its
  migration applied. Reconciling tdemo, eds and mabell gave each its ntfy login, reading only its
  own prefix. `obs` uses 965 MB of its 3.9 GB.
- **Three faults, found by the verification run and fixed:**
  - **The tenant downloads lacked provider 0.12.0 and 0.13.0.** The provider's `make stage` writes
    the Builder's copy only, and the tenant downloads on `obs` are synced from it by their own
    play, which had not run since 0.11.0. It has now.
  - **The path unit never fired.** It watched the writer's stamp file, which the writer replaces by
    rename, and a rename onto a watched file is not a change to it. It now watches the directory
    ([ansible-collection-deevnet.mgmt#135](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/135)).
  - **No tenant's vmalert started:** *"Failed to load environment files: Permission denied"*.
    systemd reads `EnvironmentFile=` itself, and SELinux denies it the writer's files under `/srv`.
    The unit's own shell, as the service user, now reads the port from the file (the same pull
    request).
- **Step 8:** the tenant Alerting page, Coming Soon, the Metrics and Dashboards pages, the platform
  pages and the Software Catalog
  ([deevnet-docs#442](https://github.com/deevnet/deevnet-docs/pull/442)), and the tdemo example,
  `alerts.tf` and the `notify` output
  ([deevnet-tenant-tdemo#21](https://github.com/deevnet/deevnet-tenant-tdemo/pull/21)).

### Verification on site (2026-11-15)

**27 of 27 checks pass**, run from a Mac on `DVNTM-TD` as eds (index 2) and mabell (index 3), with
each tenant's tokens and ntfy login read from its own state, and an Android phone subscribed to
`eds-chg0071` in ntfy:
- `ntfy.mobile.deevnet.net` resolves to `obs`.
- These are refused by ntfy: a read with no login, a wrong password, eds reading mabell's topic and
  mabell reading eds's, and eds publishing, even to its own topic.
- These are refused by the API (400): a rule labeled `tenant` with the other tenant's name, a rule
  vmalert won't load, with its reason, and a recording rule. mabell is told eds's rule groups do
  not exist (404).
- eds's metrics group and its logs group fired, each reached `eds-chg0071` and the phone, and the
  metrics alert sent a resolved notification, which the phone showed, when its value dropped.
- mabell's rule querying eds's series found nothing, and mabell's topic stayed empty.
- When the run deleted its groups, each tenant's vmalert stopped and its directory was removed.

The logs group read eds's workloads partition. The device partition's header was proven on the
Builder in Step 2, with tdemo trying eds's. Removing a tenant, which takes its alerting with its log
users, was not exercised on site; the writer's tests cover it.

The first run passed every check before the alerts, and then got only the metrics alert. vmalert had
not been running when the run wrote its log line, and a logs rule searches only its last interval.
That is now on the tenant Alerting page.
