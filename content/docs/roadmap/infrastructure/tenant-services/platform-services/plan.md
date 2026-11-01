---
title: "Tenant Platform Services: Project Plan"
linkTitle: "Project Plan"
weight: 1
tasks_completed: 7
tasks_in_progress: 0
tasks_planned: 8
---

# Tenant Platform Services: Project Plan

The services a tenant can use beyond networks, workloads and names, one of three plans for the tenant platform with [Tenant Fabric](/docs/roadmap/infrastructure/tenant-services/tenant-fabric/plan/) and [Tenant Lifecycle](/docs/roadmap/infrastructure/tenant-services/tenant-lifecycle/plan/).

**Roadmap item:** [Tenant Platform Services](/docs/roadmap/infrastructure/tenant-services/platform-services/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Platform services for tenants 🔄

What a tenant can declare today beyond networks, workloads and names, each through the provider.

- ✅ Wi-Fi keys: a PPSK key per tenant on `DVNTM-IOT`
  ([CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/))
- ✅ Device registry ([CHG-0014](/docs/changes/2026/0014-tenant-device-registry/))
- ✅ MQTT: VerneMQ, with broker accounts the API writes
  ([CHG-0015](/docs/changes/2026/0015-vernemq-broker/),
  [CHG-0016](/docs/changes/2026/0016-broker-accounts/))
- ✅ Logs: ingest and read tokens, and device logs over MQTT
  ([CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/),
  [CHG-0021](/docs/changes/2026/0021-mqtt-log-bridge/))
- ✅ Dashboards: a Grafana organization per tenant
  ([CHG-0024](/docs/changes/2026/0024-tenant-dashboards/))
- ✅ A tenant dev network, `DVNTM-TD`, reaching only the API, the state store, the broker, logs,
  Grafana and downloads ([CHG-0022](/docs/changes/2026/0022-tenant-dev-network/))
- ✅ Tenant downloads: the prebuilt provider, a laptop check and the large installers, served on
  site ([CHG-0025](/docs/changes/2026/0025-tenant-downloads/))
- ⏳ Secrets, metrics and alerting, identity and object storage: designed, not built
  ([Coming Soon](/docs/runbook/tenant/services/coming-soon/))
- ⏳ Device secrets in tenant code ([ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/)):
  the provider takes a tenant-supplied broker password and Wi-Fi key as write-only arguments, the
  restore path reads them from configuration, and `eds` and `mabell` move theirs from state into
  their repositories
- ⏳ Per-tenant resource quotas on the tenant hypervisor, so one tenant cannot use up the node
- ⏳ Workloads and DNS records come back after a rebuild: a reconcile re-ensures neither, and a tenant's plain apply sees no change. Re-ensure them in the reconcile, or give the tenant a documented way to force a re-apply

---

## Windows tenant laptops ⏳

A tenant developer needs Terraform, the `deevnet/deevnet` provider and the `grafana` provider on their
laptop. Terraform runs on Windows, but the provider's prebuilt releases are built for macOS and Linux
only, and `install-provider.sh` and `tenant-check.sh` are bash. Today a Windows laptop can't be a
tenant without building the provider from source.

- ⏳ Cross-compile the provider for Windows (`amd64` and `arm64`): add `windows` to the GoReleaser
  targets in `terraform-provider-deevnet`
- ⏳ Mirror the Windows zips, and the `grafana` provider's, in the
  [tenant downloads](/docs/changes/2026/0025-tenant-downloads/)
- ⏳ Install on Windows without bash: a PowerShell `install-provider.ps1` that puts both providers in
  Terraform's plugin directory and checks them against `SHA256SUMS`, and a Windows equivalent of
  `tenant-check.sh`
- ⏳ [Before You Start](/docs/runbook/tenant/getting-started/before-you-start/) gains the Windows
  path, proven from a Windows laptop on `DVNTM-TD`. WSL2 very likely works today with the Linux
  build, but is untested
