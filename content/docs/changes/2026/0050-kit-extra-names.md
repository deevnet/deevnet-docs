---
title: "CHG-0050: Extra Names on a Pi's Certificate (deevnet-kit 0.12.0)"
weight: -50
---

# CHG-0050: Extra Names on a Pi's Certificate (deevnet-kit 0.12.0)

| | |
|---|---|
| **Date** | 2026-10-18 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | **Complete, 2026-10-18.** `deevnet-kit` 0.12.0 released and staged; on `dv02rpi003p01` by hand, whose certificate now names both the mobile and the home site. |
| **Window** | 2026-10-18 |
| **Site** | mobile |
| **Systems** | `deevnet-provisioning-api` (`v0.12.0`); the artifact server's `binaries/deevnet-kit/` and `binaries/deevnet-log-user/`; `dv02rpi003p01`'s `/usr/local/bin/deevnet-kit` |
| **Automation** | `deevnet-provisioning-api` PR #31, tag `v0.12.0`, `make stage-pi` |
| **Risk** | Low. A card that sets no names behaves as before. On the Pi, 0.11.0 is kept beside the new binary |
| **Related changes** | [CHG-0049](/docs/changes/2026/0049-pi-backend-on-kit-0-11/), the take-home image on 0.11.0 |
| **Related incidents** | None |
| **Related runbooks** | None |

---

## Summary

A `pi-backend` card's server certificate named its hostname, `<hostname>.local`, `localhost` and
the addresses the Pi had when it was issued, and nothing else. EdS's backend Pi is on DVNTM now and
moves to its owner's home network, where it will be `192.168.2.40` and have names under
`home.deevnet.net`. Its devices are rebuilt to dial those, so the certificate has to carry them
before the Pi has them.

## What was done

- **`deevnet-kit` 0.12.0** (PR #31): extra names and addresses in `/etc/deevnet-kit/names`, one a
  line, set by `names=` in `deevnet-kit.txt` on first boot and by `deevnet-kit names
  [list|set|add|rm]` afterwards; every certificate issued carries them; wildcards refused.
  `regen-certs` now also restarts Grafana, which presents the certificate on 3000 and kept the old
  one (seen on `dv02rpi003p01` the same day). Three new tests; `go test ./...` passes on the
  Builder, and the PR's checks passed.
- **Released and staged**: tag `v0.12.0`, `make stage-pi`; `deevnet-kit-latest-linux-arm64` points
  at `deevnet-kit-v0.12.0-linux-arm64` (`5fdb7c3b…`).
- **`dv02rpi003p01`, by hand, no reflash**: the binary copied to `/usr/local/bin/deevnet-kit`, 0.11.0
  kept as `deevnet-kit.v0.11.0`; `names set` with `192.168.2.40`,
  `dv02rpi003p01.mobile.deevnet.net`, `dv01rpi001p01.home.deevnet.net`, `dv01rpi001p01`,
  `mqtt.home.deevnet.net`, `console.eds.home.deevnet.net`, `grafana.home.deevnet.net`,
  `logs.home.deevnet.net`; `regen-certs`.

## Verification

- The certificate's SANs hold every name above, `10.20.30.13`, the Wi-Fi address and `192.168.2.40`;
  valid to 2029.
- From a laptop on DVNTM, dialing `10.20.30.13` and verifying against the card's CA: the broker as
  `mqtt.home.deevnet.net`, `dv02rpi003p01.mobile.deevnet.net` and `192.168.2.40`; Grafana, the log
  store and EdS's console under their home names. `mqtt.mobile.deevnet.net` is refused.
- `deevnet-kit selftest`: 15 of 15.

### Departures

- Carried out from the operator's Mac by an assistant session, for EdS CHG-0028.
- The published `pi-backend` image is still on 0.11.0 (CHG-0049): a new card cannot take `names=`
  until it is rebuilt.

## Follow-ups

- [x] Rebuild and republish `pi-backend` on 0.12.0: [CHG-0051](/docs/changes/2026/0051-pi-backend-on-kit-0-12/).
- [ ] `deevnet-kit init` issues the CA and certificate before the clock is set: on
      `dv02rpi003p01` they began `2025-11-24`, the image's saved clock. Wait for time sync first.
- [ ] Two x86-64 binaries are committed in `deevnet-provisioning-api` (`deevnet-kit` and
      `cmd/deevnet-kit/deevnet-kit`).
