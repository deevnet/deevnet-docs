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

**Today:** none; logs are the only telemetry the platform stores for you. **Planned:** the platform
scrapes and stores your workloads' metrics in a partition of your own, you declare alert rules that
run under your own token, and notifications go out through a platform push service.
[ADR-0023](/docs/architecture/decisions/0023-metrics-and-alerting/)

## Dashboards

{{< status-badge "planned" "Coming soon" >}}

**Today:** read [logs](/docs/runbook/tenant/services/logs/) by query. **Planned:** a Grafana
organisation per tenant with your log and metrics data sources already wired in; you are an Editor
of your own organisation and manage dashboards with the Terraform `grafana` provider.
[ADR-0024](/docs/architecture/decisions/0024-dashboards/)

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

## A downloadable provider

{{< status-badge "planned" "Coming soon" >}}

**Today:** you build the provider from source
([Before you start](/docs/runbook/tenant/getting-started/before-you-start/#getting-the-provider)).
**Planned:** the provider served from the site's artifact server. The other half of this item, a
network that reaches the API and the broker and nothing else, is live as `DVNTM-TD`
([CHG-0022](/docs/changes/2026/0022-tenant-dev-network/)).
