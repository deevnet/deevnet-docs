---
title: "CHG-0051: The Take-Home Image on deevnet-kit 0.12.0"
weight: -51
---

# CHG-0051: The Take-Home Image on deevnet-kit 0.12.0

| | |
|---|---|
| **Date** | 2026-10-18 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | **Complete, 2026-10-18.** `raspios-bookworm-mobile-pi-backend.img.xz` in the tenant downloads is rebuilt with `deevnet-kit` 0.12.0, so a new card can take `names=`. |
| **Window** | 2026-10-18, one build on the Builder and one publish |
| **Site** | mobile |
| **Systems** | The artifact server's `tenant/pi/` |
| **Automation** | `deevnet-image-factory` `make pi-backend`, `make pi-backend-publish` |
| **Risk** | Low. As CHG-0049; the checksum beside the image catches a download taken mid-publish |
| **Related changes** | [CHG-0049](/docs/changes/2026/0049-pi-backend-on-kit-0-11/), the same image on 0.11.0 earlier the same day; [CHG-0050](/docs/changes/2026/0050-kit-extra-names/), the kit release this carries |
| **Related incidents** | None |
| **Related runbooks** | None |

---

## Summary

CHG-0050 released `deevnet-kit` 0.12.0, which puts extra names and addresses on a Pi's server
certificate, and left the published image on 0.11.0. A card made from that image stops on the
`names=` key. This rebuilds and republishes the image with 0.12.0, closing CHG-0050's first
follow-up.

## What was done

- `make pi-backend` in `deevnet-image-factory`, a clean tree at its `main`. The inputs took
  `deevnet-kit-latest-linux-arm64`, which points at `deevnet-kit-v0.12.0-linux-arm64`. The config
  play ended `ok=34 changed=22 failed=0`, every assertion passing.
- `make pi-backend-publish`.

## Verification

- The build's `deevnet-kit` has the SHA-256 of the staged `deevnet-kit-v0.12.0-linux-arm64`
  (`5fdb7c3b…`).
- `sha256sum -c` against the published checksum: OK. 938 MB, published 15:06, SHA-256
  `5197cccf…`.

### Departures

- Carried out from the operator's Mac by an assistant session, for EdS CHG-0028.

## Follow-ups

- [ ] The first card from it, with `names=`, on `dv02rpi003p01` (EdS CHG-0028).
