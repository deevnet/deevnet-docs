---
title: "Tenant Platform Services: Project Plan"
linkTitle: "Project Plan"
weight: 1
tasks_completed: 16
tasks_in_progress: 1
tasks_planned: 5
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
- ✅ Secrets: an optional OpenBao namespace per tenant, written through the provider and read by
  each workload under its own AppRole ([ADR-0021](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/),
  [CHG-0067](/docs/changes/2026/0067-tenant-secrets/))
- 🔄 Object storage, step one: a VM of its own, `dv02obj001v01`, running silo as a state store and
  a bucket store on separate disks, with tenants' state moved onto it and MinIO retired. Done on
  2026-11-14 but for clean plans from eds and mabell
  ([CHG-0068](/docs/changes/2026/0068-object-store-vm/),
  [ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/))
- ⏳ Object storage, step two: tenant buckets, with quotas, keys, versioning, lifecycle and
  site-only anonymous read, through `deevnet_bucket` and `deevnet_bucket_key`
  ([CHG-0069](/docs/changes/2026/0069-tenant-buckets/))
- ⏳ Metrics and alerting, and identity: designed, not built
  ([Coming Soon](/docs/runbook/tenant/services/coming-soon/))
- ⏳ Device secrets in tenant code ([ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/)):
  the provider takes a tenant-supplied broker password and Wi-Fi key as write-only arguments, the
  restore path reads them from configuration, and `eds` and `mabell` move theirs from state into
  their repositories
- ⏳ Per-tenant resource quotas on the tenant hypervisor, so one tenant cannot use up the node
- ⏳ Workloads and DNS records come back after a rebuild: a reconcile re-ensures neither, and a tenant's plain apply sees no change. Re-ensure them in the reconcile, or give the tenant a documented way to force a re-apply

---

## Windows tenant laptops ✅

A tenant developer needs Terraform, the `deevnet/deevnet` provider and the `grafana` provider on their
laptop, and a way to run the reference tenant's targets. On Windows, that works two ways, natively in
PowerShell or under WSL2, and the tenant guide documents both
([CHG-0058](/docs/changes/2026/0058-windows-tenant-laptops/)).

- ✅ Cross-compile the provider for Windows (`amd64` and `arm64`), named `.exe` as Terraform
  requires, in `make release-build` and GoReleaser. Released in v0.9.0
- ✅ Install on Windows without bash: `install-provider.ps1` into
  `%APPDATA%\terraform.d\plugins`, checked against `SHA256SUMS`, and `tenant-check.ps1` with
  `winget` hints
- ✅ `tenant-check.sh` under WSL2: networking mode, a checkout on a Windows drive, the site's names
- ✅ The reference tenant's targets without make: `tenant.ps1` in `deevnet-tenant-tdemo`, with the
  Makefile's guards and a native `state-backend`
- ✅ LF line endings in a Windows checkout: `.gitattributes` in the provider and tdemo
- ✅ Mirror Terraform, the `grafana` provider and Pi Imager for Windows in the
  [tenant downloads](/docs/changes/2026/0025-tenant-downloads/), with provider v0.9.0 and the
  `.ps1` scripts. Served
- ✅ [Before You Start](/docs/runbook/tenant/getting-started/before-you-start/) and the other tenant pages
  gain the Windows lines and a *Working from Windows* section
- ✅ Proven from a Windows laptop on `DVNTM-TD`, natively (Windows PowerShell 5.1 and PowerShell 7)
  and under WSL2, on 2026-11-07

