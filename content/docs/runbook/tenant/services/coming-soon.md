---
title: "Coming Soon"
weight: 9
---

# Coming Soon

Services that are designed — each has an architecture decision record — but not built. Nothing
here can be declared today. The shape described is the proposal's, and may change before it ships.

---

## Metrics and alerting

{{< status-badge "planned" "Coming soon" >}}

**Today:** logs are the only telemetry the platform stores for you, though a numeric field in a
device's JSON log line can already be [graphed](/docs/runbook/tenant/services/dashboards/#a-starter-dashboard).
**Planned:** your workloads push metrics into a partition of your own (the platform never scrapes a
tenant workload), you declare alert rules that run under your own token, and notifications go out
through a platform push service. Your Grafana organization gains metrics data sources beside the
log ones.
[ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/)

## Identity

{{< status-badge "planned" "Coming soon" >}}

**Today:** the API token is your tenant's identity; there are no user accounts. **Planned:** a realm
of your own in a platform identity directory, for your application's users and for SSH to your
workloads by short-lived certificate.
[ADR-0025](/docs/architecture/decisions/platform-services/0025-identity-directory/)

## Object storage

{{< status-badge "planned" "Coming soon" >}}

**Today:** the [state store](/docs/runbook/tenant/services/state-store/) holds Terraform state only.
**Planned:** S3-compatible buckets of your own for application data,
declared like everything else. [ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/)

## A tenant devbox

{{< status-badge "planned" "Coming soon" >}}

**Today:** you install the [tools](/docs/runbook/tenant/getting-started/before-you-start/#tools) on
your own computer, with the provider and the large downloads served by the site. **Planned:** a
development workload, built from an image with the tools already on it, that you launch in your own
tenant network, so the Terraform and CLI half needs nothing on your computer. Flashing a device or
an SD card still needs your computer's USB.
