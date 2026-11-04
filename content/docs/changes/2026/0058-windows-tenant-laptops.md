---
title: "CHG-0058: Windows Tenant Laptops"
weight: -58
---

# CHG-0058: Windows Tenant Laptops

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Routine |
| **Status** | Planned |
| **Window** | Unscheduled. Before the next meetup at which a tenant brings a Windows laptop |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the curated `tenant/` tree), `dv02obs001v01` (`tenant-downloads`) |
| **Automation** | `deevnet.builder` `site.yml --tags fetched-artifacts`; `terraform-provider-deevnet` `make stage` / `make release`; `deevnet.mgmt` `site.yml --tags tenant-downloads`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Files are added to a read-only tree, and nothing that is there now changes. Most likely to go wrong: the Windows scripts fail on a real laptop, and tenants on Windows stay where they are today |
| **Related changes** | [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (the tenant downloads this adds to) |
| **Related incidents** | None |
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
3. **Serve it:** `deevnet.mgmt site.yml --tags tenant-downloads --limit dv02obs001v01`.
4. **Prove it** from a Windows laptop on `DVNTM-TD`, natively and under WSL2, as in Goal.

**Undo:** remove the five entries from `artifact_servers.yml`, delete their files from the Builder's
`tenant/` tree, and rerun step 3. Its `--delete` push removes them from `obs`. A provider release
can stay: its Windows zips change nothing for macOS or Linux.

## Outcome

Not yet run.

## Follow-ups

- [ ] Run it, and fill in Outcome
