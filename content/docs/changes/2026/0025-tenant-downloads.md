---
title: "CHG-0025: Tenant Downloads"
weight: 25
---

# CHG-0025: Tenant Downloads

| | |
|---|---|
| **Date** | 2026-09-24 |
| **Change type** | Deployment · Configuration |
| **Classification** | Routine |
| **Status** | **In progress.** The downloads server is live on `obs` and verified from the Builder. `downloads.mobile.deevnet.net` resolves. Its `tenant_dev` rule was applied by the operator with CHG-0024's two (68 rules, no drift). **What remains is the check from a Mac on `DVNTM-TD`.** |
| **Window** | 2026-09-24 18:58 to 19:10 EDT |
| **Site** | mobile |
| **Systems** | `dv02obs001v01` (the new `tenant-downloads` container), `dv02cor002p01` (one DNS alias, one rule), `dv00bld001p01` (the curated tree) |
| **Automation** | `deevnet.builder` `site.yml --tags container-images,fetched-artifacts`; `terraform-provider-deevnet` `make stage` / `make release`; `deevnet-image-factory` `make pi-backend-publish`; `deevnet.mgmt` `site.yml --tags tenant-downloads`; `deevnet.net` `make dns`, `make migration-opnsense-firewall`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Read-only static files; a new service nothing depends on. What could go wrong: stale files served after an update, which the push avoids by mirroring the Builder's tree exactly (`--delete`) |
| **Related changes** | [CHG-0022](/docs/changes/2026/0022-tenant-dev-network/) (the segment), [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/) (its rules are applied with this one) |
| **Related incidents** | None |
| **Related runbooks** | [Before You Start](/docs/runbook/tenant/getting-started/before-you-start/), [Tenant Admission](/docs/runbook/substrate/tenant-admission/) |

---

## Summary

A tenant developer at a meetup needed Go and make to build the provider from source. They were
also downloading Terraform, Pi Imager, MicroPython and a 1 GB Pi image over the venue's internet.
A library's internet is slow and shared, and the site's artifact server is on management, which
the segmentation standard forbids `DVNTM-TD` to reach.

This change adds a read-only **tenant downloads** server on Platform, at
`https://downloads.mobile.deevnet.net:8443/`. It also adds a prebuilt provider (macOS and Linux,
Intel and ARM) with `install-provider.sh`, and `tenant-check.sh`, a laptop readiness check. The
tenant guide gains a prerequisites table with brew, dnf and apt install lines.

**The alternatives the operator considered:**
- **An Ansible role for tenant laptops.** Rejected: attendees would need Ansible first, and the
  `workstation` role is an operator's Fedora Builder role.
- **A route to the Builder.** Rejected: it breaks the standard.
- **A shared tenant builder VM.** Deferred: it creates a cross-tenant boundary, and the device and
  SD-card work still needs the laptop. The per-tenant devbox is on Coming Soon.

## Goal

- `https://downloads.mobile.deevnet.net:8443/` serves the Builder's `tenant/` tree read-only,
  byte for byte, over TLS from the site CA. It also serves `site-ca.pem`.
- From a scratch home directory, `install-provider.sh` installs `deevnet/deevnet` 0.4.1 and
  `grafana/grafana` 4.46.0, verified against their `SHA256SUMS`. `terraform init` then succeeds
  with no registry.
- `tenant-check.sh` reports every tool and service. `DVNTM-TD` reaches `:8443` and nothing else new.

## Procedure

1. **Curate the tree on the Builder.** The `artifacts` role (`--tags fetched-artifacts`) fetches
   Terraform 1.16.4, the `grafana` provider 4.46.0, Pi Imager 2.0.11.1 and MicroPython 1.29.0, each
   sha256-pinned. The provider's `make stage` adds the deevnet provider and the scripts. The image
   factory's `make pi-backend-publish` adds the Pi image.
2. **Serve it:** `deevnet.mgmt site.yml --tags tenant-downloads --limit dv02obs001v01`. nginx
   1.29.1 with host networking on `:8443`, a site-CA certificate, the tree pushed with rsync
   (`--delete`) and mounted read-only. Anything but GET and HEAD is refused.
3. **Name it:** a `downloads` CNAME on `obs`, `deevnet.net make dns`.
4. **Open it to `DVNTM-TD`:** one rule, `tenant_dev -> dv02obs001v01:8443`.
5. **Publish the provider:** `v0.4.1` as a GitHub release with the same zips, as the off-site route.

**Undo:** stop and disable `tenant-downloads` on `obs`, then delete `/srv/tenant-downloads`.
Remove the rule and the CNAME from inventory and apply both. The GitHub release can stay.

## Outcome

| When (EDT) | Step | What happened |
|---|---|---|
| 18:58 | 1 | The tree was fetched: 15 files, 1.3 GB. **The container-image step failed on MinIO**: quay.io now answers `unauthorized` for `quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z`. The mirrored tarball of the state store's image is still on the Builder, but it can no longer be re-pulled. nginx was mirrored with a narrowed image list |
| 19:01 | 2 | The first run failed: `limit_except` is not allowed at server level. It was moved into `location /` and the run passed. A second run is `changed=0` |
| 19:03 | 2 | Verified from the Builder: the listing works; all 15 files match the Builder's by sha256; `site-ca.pem`'s fingerprint is right; `PUT` gets `403`; nothing listens on `:80` |
| 19:05 | 5 | Provider `v0.4.1` tagged, staged and released on GitHub, with 4 zips, `SHA256SUMS` and both scripts |
| 19:06 | — | From a scratch home directory: `install-provider.sh` installed both providers from the site; `terraform init` with the network blackholed installed both from the local mirror; a tampered zip was refused (`checksum mismatch`) |
| 19:07 | — | `tenant-check.sh` on the Builder: every tool and service reported, and each missing tool came with its dnf line |
| 19:08 | 3 | CNAME added; `downloads.mobile.deevnet.net` resolves to `10.20.25.22` |
| 19:09 | 4 | Firewall plan: exactly three to add (CHG-0024's two and this one), nothing else. The automated session may not apply core-router rules |
| later | 4 | **Applied by the operator.** The re-plan shows 0 to add and 68 rules, with no drift |
| 19:59 | — | From a tenant laptop on `DVNTM-TD`: `tenant-check.sh` first reported the provider missing, then `install-provider.sh` installed it from the site and every check passed. `segment-check.sh DVNTM-TD` passed 29/29: `downloads` resolves, `:8443` is reachable over verified TLS, and `obs`'s SSH is blocked |

### Departures from the plan

- The segmentation standard now names all six tenant-facing services. CHG-0024 had opened the log
  store and Grafana without amending it.
- ADR-0012 §7 said laptops copy the provider mirror from the artifact server. That is amended:
  the artifact server is on management.

## Follow-ups

- [x] Apply the three `tenant_dev` rules (with CHG-0024's two), by the operator
- [x] From a `DVNTM-TD` laptop: `tenant-check.sh`, `install-provider.sh` and
      `segment-check.sh DVNTM-TD`, all passing
- [ ] From IoT: `segment-check.sh DVNTM-IOT` with net #37's `obs` checks
- [ ] MinIO's image can no longer be pulled from quay.io. Keep the mirrored tarball, and weigh this
      in [ADR-0026](/docs/architecture/decisions/0026-object-storage/)
- [ ] Before each meetup: restage anything that changed, then run `--tags tenant-downloads`
