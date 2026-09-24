---
title: "🔀 Change Records"
weight: 6
bookCollapseSection: true
aliases:
  - /docs/migrations/
---

# Change Records

One record per significant change to a site: what was changed and why, the end state it
aimed for, the procedure, how to undo it, and what actually happened.

The [runbook](/docs/runbook/) and these records hold different kinds of information. The
runbook is **maintained**: procedures and templates, kept current, and edited whenever
reality changes. A change record is **retained**: evidence of a change made on a given day.
It is written once and then left alone, apart from follow-ups closing. Incidents are kept
the same way, under [Incident Records](/docs/incidents/).

New records start from the [change record template](/docs/policies/change-management/change-record-template/).
[Change Management](/docs/policies/change-management/) says when a change needs one.

---

## Records

| ID | Date | Change | Type | Site | Status |
|---|---|---|---|---|---|
| CHG-0001 | 2026-03-21 | [Flat Network → VLANs](2026/0001-flat-network-to-vlans/) | Migration | mobile | Complete |
| CHG-0002 | 2026-03-26 | [Authority Transition Rework](2026/0002-authority-transition-rework/) | Configuration | mobile | Complete |
| CHG-0003 | 2026-09-05 | [Host Rename (ADR-0008)](2026/0003-host-rename/) | Migration | mobile | Complete |
| CHG-0004 | 2026-09-10 | [Omada Controller Upgrade](2026/0004-omada-controller-upgrade/) | Upgrade | mobile | Complete |
| CHG-0005 | 2026-09-15 | [Wireless AP Firmware and Omada Adoption](2026/0005-wireless-ap-firmware-and-adoption/) | Migration | mobile | Complete |
| CHG-0006 | 2026-09-16 | [Access Switch Firmware Upgrade](2026/0006-access-switch-firmware-upgrade/) | Upgrade | mobile | Complete |
| CHG-0007 | 2026-09-19 | [Core Router Zone Policy, First Application](2026/0007-core-router-zone-policy/) | Configuration | mobile | Complete |
| CHG-0008 | 2026-09-15 | [Management Domain VMs, First Build](2026/0008-domain-vms-build-out/) | Deployment · Decommission | mobile | Complete |
| CHG-0009 | Unscheduled | [Access Switch Omada Adoption](2026/0009-access-switch-adoption/) | Migration | mobile | Planned (on hold) |
| CHG-0010 | 2026-09-17 | [Deploy the Deevnet API and Cut Tenants Over](2026/0010-tenant-api-cutover/) | Build-out and migration | mobile | Complete |
| CHG-0011 | 2026-09-17 | [Tenant Workloads Get a Resolver](2026/0011-tenant-workload-resolver/) | Configuration · Deployment | mobile | Complete |
| CHG-0012 | 2026-09-18 | [Operator Access to Tenant Workloads](2026/0012-operator-access-to-tenants/) | Configuration | mobile | Complete |
| CHG-0013 | 2026-09-18 | [Tenant Wi-Fi PPSK Keys](2026/0013-tenant-wifi-ppsk-keys/) | Deployment | mobile | Complete |
| CHG-0014 | 2026-09-20 | [The Tenant Device Registry](2026/0014-tenant-device-registry/) | Deployment | mobile | Complete |
| CHG-0015 | 2026-09-20 | [The VerneMQ Broker](2026/0015-vernemq-broker/) | Deployment | mobile | Complete |
| CHG-0016 | 2026-09-20 | [The API Writes Broker Accounts](2026/0016-broker-accounts/) | Deployment · Configuration | mobile | Complete |
| CHG-0017 | 2026-09-20 | [Retire Mosquitto](2026/0017-retire-mosquitto/) | Configuration · Cleanup | mobile | Complete |
| CHG-0018 | 2026-09-21 | [The Central Log Store](2026/0018-central-log-store/) | Deployment · Configuration | mobile | Complete |
| CHG-0019 | 2026-09-22 | [Strip the Log Store to Tenant Scope](2026/0019-log-store-tenant-scope/) | Configuration · Decommission | mobile | Complete |
| CHG-0020 | 2026-09-22 | [The API Issues Tenant Log Tokens](2026/0020-tenant-log-tokens/) | Deployment · Configuration | mobile | Complete |
| CHG-0021 | 2026-09-22 | [The MQTT Log Bridge](2026/0021-mqtt-log-bridge/) | Deployment | mobile | Complete |
| CHG-0022 | 2026-09-23 | [The Tenant Dev Network](2026/0022-tenant-dev-network/) | Configuration | mobile | Complete |
| CHG-0023 | 2026-09-23 | [Internet Means Internet](2026/0023-internet-means-internet/) | Configuration | mobile | Complete |
| CHG-0024 | 2026-09-24 | [Tenant Dashboards](2026/0024-tenant-dashboards/) | Deployment · Configuration | mobile | In progress |
| CHG-0025 | 2026-09-24 | [Tenant Downloads](2026/0025-tenant-downloads/) | Deployment · Configuration | mobile | In progress |

Records are numbered `CHG-NNNN` in the order they are opened, like
[ADRs](/docs/architecture/decisions/): the number is global, never reused, and is how a record
is cited. They are grouped by year, and each carries the date execution started.

## Retrospective records

Changes made before this section existed are written up **retrospectively**. Each one is
rebuilt from the plan that drove the change, the automation logs, and git history, and says
so at the top. A retrospective record reshapes what was captured at the time. Where the
original material is silent, the record says so rather than filling the gap.
