---
title: "CHG-0058: Windows Tenant Laptops"
weight: -58
---

# CHG-0058: Windows Tenant Laptops

| | |
|---|---|
| **Date** | 2026-11-04 |
| **Change type** | Deployment · Configuration |
| **Classification** | Routine |
| **Status** | Complete |
| **Window** | Unscheduled. Before the next meetup at which a tenant brings a Windows laptop |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the curated `tenant/` tree), `dv02obs001v01` (`tenant-downloads`) |
| **Automation** | `deevnet.builder` `site.yml --tags fetched-artifacts`; `terraform-provider-deevnet` `make stage` / `make release`; `deevnet.mgmt` `site.yml --tags tenant-downloads`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium. Step 3 pushes about 250 MB from the Builder to `obs` across the core router's `re0`, the same kind of transfer that hard-hung it in [INC-0004](/docs/incidents/2026/0004-core-router-lost/) and [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/), both still open. The operator is at the router's console for step 3. Otherwise files are only added to a read-only tree, and nothing there now changes. Also likely: the Windows scripts fail on a real laptop, and tenants on Windows stay where they are today |
| **Related changes** | [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (the tenant downloads this adds to) |
| **Related incidents** | [INC-0004](/docs/incidents/2026/0004-core-router-lost/), [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/) (the router's `re0` under bulk transfer) |
| **Related runbooks** | [Before You Start](/docs/runbook/tenant/getting-started/before-you-start/), [Tenant Admission](/docs/runbook/substrate/tenant-admission/) |

---

## Summary

A tenant developer with a Windows laptop could not take part without building the provider from
source. The prebuilt provider was for macOS and Linux only, and both scripts and the reference tenant's
Makefile need bash. The tenant downloads served no Windows Terraform, `grafana` provider or Pi Imager.

This change adds those to the tenant downloads and publishes a provider release that carries:

- `windows_amd64` and `windows_arm64` builds
- `install-provider.ps1` and `tenant-check.ps1`
- a `tenant-check.sh` that knows WSL2

The reference tenant gains `tenant.ps1`, its Makefile in PowerShell. The tenant guide covers both
Windows routes: native PowerShell, and WSL2 with mirrored networking.

**The alternative the operator considered:**
- **WSL2 only.** Rejected as the only route: it needs `usbipd-win` for a board over USB and a
  `.wslconfig` before the site's names resolve. A laptop that only applies Terraform shouldn't need
  either. WSL2 stays documented beside native.

## Goal

- The tenant downloads serve, beside the existing macOS and Linux files, verified against their
  vendors' checksums:
  - Terraform 1.16.4 and `grafana/grafana` 4.46.0, each for `windows_amd64` and `windows_arm64`
  - Raspberry Pi Imager 2.0.11.1's `.exe`
- `provider/<version>/` carries the two Windows zips, and `scripts/` carries both `.ps1` scripts.
- From a Windows 11 laptop on `DVNTM-TD`, natively:
  - `install-provider.ps1` installs both providers in Windows PowerShell 5.1 and in PowerShell 7.
  - `tenant-check.ps1` reports nothing missing.
  - A scratch tenant goes through `tenant.ps1 new`, `init`, `apply`, `state-backend` and `plan`,
    and then `destroy`.
- From the same laptop under WSL2: `tenant-check.sh` reports mirrored networking, and a plan of the
  scratch tenant succeeds.

## Procedure

1. **Curate the tree on the Builder:** `deevnet.builder site.yml --tags fetched-artifacts` fetches
   the five new files from `artifact_servers.yml`, each sha256-pinned.
2. **Release the provider:** tag the next version in `terraform-provider-deevnet`, then `make stage`
   (into the Builder's tree) and `make release` (GitHub, the off-site route).
3. **Serve it,** with the operator at the router's console: push only this change's files (the five downloads, `provider/0.9.0/` and `scripts/`) to `obs`, with the role's ownership and modes. The role's full push would also carry the Builder's newer Pi image, about 900 MB; that waits for its own window.
4. **Prove it** from a Windows laptop on `DVNTM-TD`, natively and under WSL2, as in Goal.

**Undo:** remove the five entries from `artifact_servers.yml`, delete their files from the Builder's
`tenant/` tree, and rerun step 3. Its `--delete` push removes them from `obs`. A provider release
can stay: its Windows zips change nothing for macOS or Linux.

## Outcome

Steps 1 to 3 ran on 2026-11-04 and step 4 on 2026-11-07. Windows tenants now work from their own
laptops, natively and under WSL2, from the tenant downloads alone.

| Step | Result |
|---|---|
| 1 | The five files are in the Builder's `tenant/` tree, each matching its pin. The four zips also match their vendors' `SHA256SUMS` |
| 2 | Provider **v0.9.0** ([#28](https://github.com/deevnet/terraform-provider-deevnet/pull/28)): the GitHub release carries all six zips, `SHA256SUMS` and the four scripts. `make stage` put it in the Builder's tree, and `SHA256SUMS` verifies there |
| 3 | 16 files, 177 MB, pushed to `dv02obs001v01` in 37 seconds, capped at 5 MB/s, with the operator at the router's console. The router answered throughout. Checksums computed on `obs` match the Builder's, and `downloads.mobile.deevnet.net` serves the files over TLS verified against the Deevnet Root CA |
| 4 | From a Windows 11 laptop on `DVNTM-TD`, following the tenant guide as a tenant would: `install-provider.ps1` installed both providers in Windows PowerShell 5.1 and in PowerShell 7, and `tenant-check.ps1` reported nothing missing. The scratch tenant `wtest` went through `tenant.ps1 new`, `init`, `apply`, `state-backend`, `plan` and `destroy`. Under WSL2, `tenant-check.sh` reported mirrored networking and a plan of `wtest` succeeded |

### Departures from the plan

- **Step 1 ran on the Builder alone** (`--limit dv00bld001p01`). The play also targets
  `dv02bld001v01`, which would have fetched the whole artifact set across the core router.
- **Step 3 pushed only this change's files**, with the role's ownership and modes and without
  `--delete`, not the role's whole tree. The whole tree would also have carried the Builder's
  newer Pi image, about 900 MB, which waits for its own window.
- **Step 4 changed the tenant guide** ([#374](https://github.com/deevnet/deevnet-docs/pull/374)).
  The laptop ran into: a second network routing the site's subnet out the wrong interface, WSL2
  without `dnsTunneling`, a fresh WSL distribution without `unzip`, the Root CA fingerprint
  snippet, a partial clone of the reference tenant, and a bare `terraform output` without
  `.backend.env`. The guide now covers each.
- **The destroy could not save its state.** Every API delete returned `204`, the tenant's last at
  19:33:07 UTC, but deleting the tenant also removes its Wi-Fi key and its state-store login, so
  Terraform could neither write state nor release its lock. The operator ran
  `make purge-tenant-state NAME=wtest`, and Troubleshooting now sends a tenant in the same place to
  the operator.
- **Nothing of `wtest` is left** but the Grafana organization `deleted-wtest-11`, as
  [Tenant Removal](/docs/runbook/substrate/tenant-removal/) expects. Proxmox, PowerDNS, VerneMQ,
  the state store and vmauth were checked directly. The API logged no warning or error for the
  delete, which fails on any backend step, the Omada key included. `wtest` never had a certificate
  signed, so OpenBao holds nothing for it.

## Follow-ups

- [x] Step 4: prove it from a Windows 11 laptop on `DVNTM-TD`, natively (Windows PowerShell 5.1
  and PowerShell 7) and under WSL2, as in Goal
