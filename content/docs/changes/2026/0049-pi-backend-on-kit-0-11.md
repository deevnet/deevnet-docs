---
title: "CHG-0049: The Take-Home Image on deevnet-kit v0.11.0"
weight: -49
---

# CHG-0049: The Take-Home Image on deevnet-kit v0.11.0

| | |
|---|---|
| **Date** | 2026-10-18 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | **Complete, 2026-10-18.** `raspios-bookworm-mobile-pi-backend.img.xz` in the tenant downloads is rebuilt with `deevnet-kit` v0.11.0, in place of the 2026-09-24 build with v0.8.1. |
| **Window** | 2026-10-18, one build on the Builder and one publish |
| **Site** | mobile |
| **Systems** | The artifact server: `binaries/deevnet-kit/`, `binaries/deevnet-log-user/` and `tenant/pi/` |
| **Automation** | `deevnet-provisioning-api` `make stage-pi`; `deevnet-image-factory` `make pi-backend`, `make pi-backend-publish` |
| **Risk** | Low. A tenant downloading the image mid-publish could take a mixed file; the checksum beside it would catch it |
| **Related changes** | [CHG-0025](/docs/changes/2026/0025-tenant-downloads/), which first published the image |
| **Related incidents** | None |
| **Related runbooks** | None |

---

## Summary

The published take-home image carried `deevnet-kit` v0.8.1, built on 2026-09-24. That kit stops on a
`hostname=` or `wifi_*` line in `deevnet-kit.txt` and has no `account add --password-file`, which the
image's own README tells an owner to use. The kit's source has been at v0.11.0 since then, and was never
staged for the Pi. EdS, the first tenant to build on the image (EdS ADR-0033), needs both.

## What was done

- **Staged the kit**: `make stage-pi` in `deevnet-provisioning-api` at `v0.11.0`, a clean tree.
  `deevnet-kit-latest-linux-arm64` now points at `deevnet-kit-v0.11.0-linux-arm64`, and
  `deevnet-log-user` with it.
- **Built the image**: `make pi-backend` in `deevnet-image-factory` at `bf3258b`, a clean tree. The
  config play ended `ok=34 changed=22 failed=0`, with every assertion passing.
- **Published it**: `make pi-backend-publish`, which wrote the image and its `.sha256` to
  `tenant/pi/`.

The other inputs were not restaged: the log bridge, VictoriaLogs, vmauth, Grafana and its plugin are
the versions the September image had.

## Verification

- The build's `deevnet-kit` has the same SHA-256 as the staged `deevnet-kit-v0.11.0-linux-arm64`
  (`145433a8…`).
- `sha256sum -c` against the published checksum: OK. 941 MB, 2026-10-18 10:47.

### Departures

- Carried out from the operator's Mac, through the Builder, by an assistant session, for EdS's
  one-Pi trial (EdS CHG-0028).

## Follow-ups

- [ ] The image on a real Pi: the first EdS card is built on it and booted on `dv02rpi003p01`
      (EdS CHG-0028), which will show whether Grafana's VictoriaLogs plugin registers this time.
