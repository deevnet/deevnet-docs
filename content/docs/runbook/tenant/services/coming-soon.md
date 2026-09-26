---
title: "Coming Soon"
weight: 9
---

# Coming Soon

Services that are designed — each has an architecture decision record — but not built. Nothing
here can be declared today. The shape described is the proposal's, and may change before it ships.

---

## Secrets

{{< status-badge "planned" "Coming soon" >}}

**Today:** anything secret your application needs lives in your Terraform state or your own
tooling. **Planned:** a namespace of your own in the platform secrets store, holding a runtime copy
of secrets your repository owns, written through the API, and read by your workloads with their own
identity. [ADR-0021](/docs/architecture/decisions/0021-tenant-secrets/)

## Metrics and alerting

{{< status-badge "planned" "Coming soon" >}}

**Today:** logs are the only telemetry the platform stores for you, though a numeric field in a
device's JSON log line can already be [graphed](/docs/runbook/tenant/services/dashboards/#a-starter-dashboard).
**Planned:** your workloads push metrics into a partition of your own (the platform never scrapes a
tenant workload), you declare alert rules that run under your own token, and notifications go out
through a platform push service. Your Grafana organization gains metrics data sources beside the
log ones.
[ADR-0023](/docs/architecture/decisions/0023-metrics-and-alerting/)

## Identity

{{< status-badge "planned" "Coming soon" >}}

**Today:** the API token is your tenant's identity; there are no user accounts. **Planned:** a realm
of your own in a platform identity directory, for your application's users and for SSH to your
workloads by short-lived certificate.
[ADR-0025](/docs/architecture/decisions/0025-identity-directory/)

## Object storage

{{< status-badge "planned" "Coming soon" >}}

**Today:** the [state store](/docs/runbook/tenant/services/state-store/) holds Terraform state only.
**Planned:** S3-compatible buckets of your own for application data,
declared like everything else. [ADR-0026](/docs/architecture/decisions/0026-object-storage/)

## Code delivery to workloads

{{< status-badge "planned" "Coming soon" >}}

**Today:** a workload boots Fedora with nothing of yours on it, and — because
[`ssh_keys` is broken](/docs/runbook/tenant/services/network-and-workloads/#getting-onto-it) — the
operator installs your code for you. **Planned:** a workload fetches a Deevnet-shaped description of
what to run at boot, so declaring the workload is enough to have it running your code.
[ADR-0017](/docs/architecture/decisions/0017-tenant-code-delivery/)

## A tenant devbox

{{< status-badge "planned" "Coming soon" >}}

**Today:** you install the [tools](/docs/runbook/tenant/getting-started/before-you-start/#tools) on
your own laptop, with the provider and the large downloads served by the site. **Planned:** a
development workload, built from an image with the tools already on it, that you launch in your own
tenant network, so the Terraform and CLI half needs nothing on your laptop. Flashing a device or an
SD card still needs your laptop's USB. It waits on
[`ssh_keys`](/docs/runbook/tenant/services/network-and-workloads/#getting-onto-it) and on
[code delivery](#code-delivery-to-workloads).
