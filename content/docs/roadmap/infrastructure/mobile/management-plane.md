---
title: "Extended Management Plane"
weight: 3
tasks_completed: 10
tasks_in_progress: 9
tasks_planned: 23
---

# Extended Management Plane

Extended management services for the mobile (mobile) site — logging, telemetry, alerting, secrets, and identity. Builds on the core substrate once it is operational.

- **GitHub:** https://github.com/deevnet/ansible-collection-deevnet.mgmt
- **Documentation:** https://deevnet.github.io/deevnet-docs/

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Deploy a unified management plane providing observability, security, and identity services for all substrate components, running as tenants on the Proxmox hypervisor.

**In Scope**
- Centralized logging aggregation and search
- Metrics collection and telemetry
- Alerting and notification
- Secrets management
- Identity and access management
- Ansible automation via `deevnet.mgmt` collection

**Out of Scope**
- Application-specific monitoring (handled per-tenant)
- External identity federation (future phase)
- Multi-site federation

---

## Requirements 🔄

- ✅ Define service selection criteria: each service's choice is its own ADR, weighing alternatives
  against the site's constraints (offline operation, memory, tenancy)
  ([ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/) to
  [ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/))
- 🔄 Define retention policies (logs, metrics): logs have one retention period and a disk cap for
  the whole store ([ADR-0022](/docs/architecture/decisions/0022-central-logging/) §6); metrics wait
  on ADR-0023
- 🔄 Define alerting channels and escalation: proposed in
  [ADR-0023](/docs/architecture/decisions/0023-metrics-and-alerting/) (one Alertmanager to ntfy on
  Platform). Open: who watches the watcher, and reaching an off-site phone
- ✅ Define secrets access policies: every OpenBao client is an AppRole whose policy names exactly
  its paths ([ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/)); the image
  factory's is read-only ([CHG-0026](/docs/changes/2026/0026-build-secrets/))
- 🔄 Define identity/RBAC model: proposed in
  [ADR-0025](/docs/architecture/decisions/0025-identity-directory/)

---

## Centralized Logging 🔄

One log store on Platform: VictoriaLogs behind vmauth on `dv02obs001v01`, partitioned by tenant
index. [ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/) narrowed it to **tenants
only**: the substrate's own logs are not centralized.

- ✅ Evaluate logging stack: VictoriaLogs, over Loki and Logstash with OpenSearch
  ([ADR-0022](/docs/architecture/decisions/0022-central-logging/))
- ✅ Deploy log aggregation service ([CHG-0018](/docs/changes/2026/0018-central-log-store/)), cut to
  tenant scope ([CHG-0019](/docs/changes/2026/0019-log-store-tenant-scope/))
- ✅ Tenant ingest and read tokens, issued by the Deevnet API
  ([CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/))
- ✅ Edge-device logs over MQTT into `(index, 2)`, through the MQTT log bridge
  ([CHG-0021](/docs/changes/2026/0021-mqtt-log-bridge/))
- 🔄 Deploy log visualization: Grafana OSS, one organisation per tenant, deployed and verified
  ([CHG-0024](/docs/changes/2026/0024-tenant-dashboards/)). Done when the tenants have their
  passwords and CHG-0024 closes
- ✅ Define log retention and rotation ([ADR-0022](/docs/architecture/decisions/0022-central-logging/) §6)
- Not pursued: shipping the substrate hosts' logs. CHG-0018 started it and CHG-0019 removed it
  under ADR-0027. Not counted

**Deferred from ADR-0022's v1.** Each waits on something named, rather than being unplanned:

- ⏳ Tenant events from services the site doesn't write. v1 publishes only the Deevnet API's events
  into a tenant's `(index, 1)`. A collector that maps PowerDNS and VerneMQ lines to a tenant gets its
  own record, once those lines are shown to identify the tenant reliably (Open question 3)
- ⏳ Per-workload ingest tokens, so one workload can be revoked alone. v1 issues one per tenant.
  Waits on [ADR-0021](/docs/architecture/decisions/0021-tenant-secrets/)'s delivery path (Open
  question 5)
- ⏳ Per-tenant quotas. v1 has one disk cap and one retention period, so a noisy tenant shortens
  everyone's history. Revisit when VictoriaLogs has per-tenant quotas, or if it happens (Open
  question 4)
- ⏳ Operator queries across tenants. v1 reads one partition at a time. Revisit when VictoriaLogs
  ships multi-tenant querying (Open question 1)
- ⏳ Re-measure `obs`'s memory and disk at site volume. Measured so far at one host's volume, before
  tenants shipped

---

## Telemetry 🔄

- 🔄 Evaluate metrics stack: VictoriaMetrics cluster beside the logs, fed by vmagent, proposed in
  [ADR-0023](/docs/architecture/decisions/0023-metrics-and-alerting/)
- ⏳ Deploy metrics collection service
- ⏳ Configure exporters on substrate hosts
- ⏳ Deploy metrics dashboards. Grafana itself is up since
  [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/); it has no metrics data sources yet
- ⏳ Define metrics retention

---

## Alerting 🔄

- 🔄 Evaluate alerting solutions: vmalert per tenant, one Alertmanager, ntfy, proposed in
  [ADR-0023](/docs/architecture/decisions/0023-metrics-and-alerting/). Grafana's own alerting is off
  ([ADR-0024](/docs/architecture/decisions/0024-dashboards/))
- ⏳ Deploy alerting service
- ⏳ Define alert rules for infrastructure
- ⏳ Configure notification channels (email, webhook, etc.)

---

## Secrets Management 🔄

OpenBao on `dv02idn001v01`, unsealed by a key ansible-vault delivers, which stays the root of trust
([ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/)).

- ✅ Migrate IaC secrets from env var lookups to Ansible Vault in inventory
- ✅ Evaluate dedicated secrets solutions: OpenBao
  ([ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/))
- ✅ Deploy secrets management service ([CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/))
- 🔄 Integrate consumers: the Deevnet API reads its backend credentials at start
  ([CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/)), and image-factory and tenant-fabric
  builds fetch the Proxmox token per run, with nothing on the Builder's disk
  ([CHG-0026](/docs/changes/2026/0026-build-secrets/)). Ansible administers OpenBao through its own
  AppRole, but most playbook secrets are still read from ansible-vault in inventory
- ⏳ Define secrets rotation policies ([Credential Rotation](/docs/roadmap/infrastructure/credential-rotation/))

---

## Identity Management 🔄

- 🔄 Evaluate identity solutions: Keycloak, with a realm per tenant, proposed in
  [ADR-0025](/docs/architecture/decisions/0025-identity-directory/)
- ⏳ Deploy identity provider
- ⏳ Configure SSO for infrastructure services
- ⏳ Define RBAC policies

---

## Build Verification 🔄

Automated verification that the site was built according to inventory and is fully functional. Produces a single report proving build correctness.

- ⏳ Inventory conformance checks (running state matches inventory definitions)
- 🔄 Network connectivity matrix (verify all expected paths work): `segment-check.sh` proves what
  each SSID profile reaches and is refused, from a real client
  ([Segment Check](/docs/runbook/substrate/network/segment-check/)). Segments with no SSID aren't
  covered
- ⏳ Service health checks (DNS, DHCP, PXE, Proxmox API)
- ⏳ Hardware validation (MAC addresses, IP assignments match inventory)
- ⏳ Build report generation (consolidated pass/fail with evidence)

---

## Documentation ⏳

- ⏳ Management plane architecture overview
- ⏳ Service deployment runbook
- ⏳ Operations and troubleshooting guide
