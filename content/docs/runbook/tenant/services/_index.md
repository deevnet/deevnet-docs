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
| [Devices & MQTT](devices-and-mqtt/) | `deevnet_iot_device`, `deevnet_iot_broker_account` | {{< status-badge "active" "Available" >}} |
| [Logs](logs/) | attributes of `deevnet_tenant` | {{< status-badge "active" "Available" >}} |
| [State store](state-store/) | attributes of `deevnet_tenant` | {{< status-badge "active" "Available" >}} |
| [Coming soon](coming-soon/) | — | {{< status-badge "planned" "Coming soon" >}} |

Every resource takes `tenant = deevnet_tenant.this.name`, and changing `tenant` or `name` on any of
them replaces it. None of them has a data source; what the substrate issued you comes back as
attributes of the resources themselves.
