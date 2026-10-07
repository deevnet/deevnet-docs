---
title: "Services"
weight: 3
bookCollapseSection: true
---

# Services

One page per service a tenant can declare. Each says what you get, the Terraform resource that
declares it, how a device or a workload uses it, and what it does not do yet.

| Service | Resource | Status |
|---|---|---|
| [Network & workloads](network-and-workloads/) | `deevnet_tenant`, `deevnet_workload` | {{< status-badge "active" "Available" >}} |
| [DNS](dns/) | `deevnet_dns_record` | {{< status-badge "active" "Available" >}} |
| [Wi-Fi keys](wifi-keys/) | `deevnet_iot_wifi_key` | {{< status-badge "active" "Available" >}} |
| [Devices & MQTT](devices-and-mqtt/) | `deevnet_iot_device`, `deevnet_iot_broker_account`, `deevnet_iot_address` | {{< status-badge "active" "Available" >}} |
| [Logs](logs/) | attributes of `deevnet_tenant` | {{< status-badge "active" "Available" >}} |
| [Dashboards](dashboards/) | attributes of `deevnet_tenant`; dashboards with the `grafana` provider | {{< status-badge "active" "Available" >}} |
| [State store](state-store/) | attributes of `deevnet_tenant` | {{< status-badge "active" "Available" >}} |
| [Code delivery to workloads](/docs/runbook/tenant/deploy-your-app/) | `ssh_keys` on `deevnet_workload`; you push over SSH | {{< status-badge "active" "Available" >}} |
| [Your own secrets](/docs/runbook/tenant/deploy-your-app/#your-own-secrets) | your repository, encrypted; pushed with your settings | {{< status-badge "active" "Available" >}} |
| [Metrics & alerting](coming-soon/#metrics-and-alerting) | — | {{< status-badge "planned" "Coming soon" >}} |
| [Identity](coming-soon/#identity) | — | {{< status-badge "planned" "Coming soon" >}} |
| [Object storage](coming-soon/#object-storage) | — | {{< status-badge "planned" "Coming soon" >}} |
| [A tenant devbox](coming-soon/#a-tenant-devbox) | — | {{< status-badge "planned" "Coming soon" >}} |

Every resource takes `tenant = deevnet_tenant.this.name`, and changing `tenant` or `name` on any of
them replaces it. None of them has a data source; what the substrate issued you comes back as
attributes of the resources themselves.
