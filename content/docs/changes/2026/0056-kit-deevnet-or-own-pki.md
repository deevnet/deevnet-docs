---
title: "CHG-0056: A Deevnet Pi by Default, With a Starter PKI Kit"
weight: -56
---

# CHG-0056: A Deevnet Pi by Default, With a Starter PKI Kit

| | |
|---|---|
| **Date** | 2026-10-25 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **In progress.** Steps 1 and 2 built, and verified on a Pi of the Pi lab, 2026-11-08: V7, V8 and V11 passed. Step 3 waits on the kit's release and the image's push to the tenant downloads |
| **Window** | Unscheduled. After [CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/) (site-less names to issue); one `deevnet-kit` release, one image build, the image staged to the tenant downloads |
| **Site** | mobile |
| **Systems** | `deevnet-kit`; the take-home image `raspios-bookworm-mobile-pi-backend.img.xz`; the tenant downloads on `dv02obs001v01`; one Pi of the Pi lab for the test |
| **Automation** | `deevnet-provisioning-api` (`cmd/deevnet-kit`), `deevnet-image-factory` `make pi-backend`, `deevnet.mgmt` `scripts/pki/` |
| **Risk** | Medium. Most likely to go wrong: a card that sets nothing changes behavior on upgrade. `deevnet` is the default and keeps today's first boot until a certificate is installed |
| **Related changes** | [CHG-0050](/docs/changes/2026/0050-kit-extra-names/), [CHG-0051](/docs/changes/2026/0051-pi-backend-on-kit-0-12/) (the image this replaces), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) |
| **Related incidents** | None |
| **Related runbooks** | [Pi Lab](/docs/runbook/tenant/pi-lab/) |

---

## Summary

A take-home Pi makes its own CA at first boot today, and its certificates are trusted by nothing.
[ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/) makes it a
Deevnet Pi by default: its server certificate is signed by the Tenant Service CA from a request it
makes, and its devices' certificates by the Tenant Device CA. A `non-deevnet` card instead gets a
starter kit, `deevnet-kit pki init`, that walks its owner through a two-tier PKI of their own: the
root on an encrypted USB stick, an issuing CA on the Pi
([review](/docs/architecture/reviews/2026-10-tenant-pki/), phase P7).

## Goal

- The card's first-boot configuration takes `pki=deevnet` (the default) or `pki=non-deevnet`.
- `deevnet-kit` makes a server key and a request, writes the request where it can be carried, and
  installs a certificate and its chain from a work session. The same three steps renew it.
- A Deevnet Pi's own services dial its names, mapped to loopback; its certificate carries neither
  `localhost`, an address nor a site broker's name.
- The ceremony tools take parameters for an owner's names, and issue a leaf.
- Every image carries them. `deevnet-kit pki init` asks for the owner's organization, the Pi's
  names and a USB stick, makes the root on the stick and an issuing CA on the Pi, installs the Pi's
  certificate and exports the root.
- A `non-deevnet` card keeps today's first-boot certificate until `pki init` runs.

## Scope

**In scope:** `deevnet-kit` (the switch, request and install, `pki init`), the ceremony tools'
parameters and leaf step, the image, the downloads, the Pi Lab pages.
**Out of scope:** the Mobile Factory's signing of a Pi's request beyond what CHG-0054 issues;
removing the tools from the operator's own Pis, which is a post-deploy task of each.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| An existing card changes behavior | take-home Pis | `deevnet` keeps today's first boot until a certificate is installed |
| The owner's root key left on the Pi | `non-deevnet` Pis | `pki init` writes it only to the stick, and refuses an unencrypted one |
| The ceremony tools changed for Deevnet's own ceremonies | `scripts/pki/` | Deevnet's names stay the defaults; a ceremony run with no parameters is unchanged |

## Prerequisites

- [x] CHG-0054 complete
- [x] One Pi of the Pi lab and a USB stick for the test

## Procedure

### Step 1: The ceremony tools

Parameters for names, and a leaf step.

**Verify:** a ceremony run with no parameters produces the same subjects and constraints as before.

### Step 2: `deevnet-kit`

The switch, request and install, `pki init`.

**Verify:** V7 and V11 against the test Pi.

### Step 3: The image

Build with `make pi-backend`, stage to the downloads.

**Verify:** a new card boots as `deevnet` with today's behavior until a certificate is installed.

## Verification

V7, V8 and V11 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass.

## Undo

The previous image stays in the downloads until this one is verified.

## Outcome

Built in [deevnet-provisioning-api#38](https://github.com/deevnet/deevnet-provisioning-api/pull/38),
released in **v0.15.0** with the API, and staged for the Pi (`make stage-pi`). The image was rebuilt
on it (`make pi-backend`), published to the Builder's tenant downloads tree, and served from
`dv02obs001v01` since 2026-11-04.

| Step | Result |
|---|---|
| 1 | **Built, 2026-11-08** ([ansible-collection-deevnet.mgmt#103](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/103)). `deevnet-pki-owner.sh`: `init` makes the owner's root on an encrypted USB stick and an issuing CA on the Pi; `issuing` makes a new card's issuing CA from the root on the stick; `leaf server` and `leaf device` issue from the issuing CA. The issuing CA may name only the owner's domains, `.local`, `localhost`, and private and loopback addresses, and a leaf naming anything else is refused before it is written. The root key goes only to an encrypted mount; a plain stick or a directory on the Pi is refused. `deevnet-pki-media.sh` labels the owner's stick `owner-keys-primary`, which Deevnet's own key media lookup does not find. `deevnet-pki.cnf` and `deevnet-pki-ceremony.sh` are unchanged, so a ceremony run with no parameters is the same as before. Tested on the Builder, and against a LUKS2 loop device in a Bookworm container |
| 2 | **Built, 2026-11-08** ([deevnet-provisioning-api#50](https://github.com/deevnet/deevnet-provisioning-api/pull/50), [#51](https://github.com/deevnet/deevnet-provisioning-api/pull/51)). `deevnet-kit pki init` runs the tool and checks what it made: the issuing CA chains to the root beside it, has `pathlen:0` and name constraints, and no root key is on the Pi. Nothing served changes, and `export` hands out `trust-bundle.pem`, the root trusted now and the owner's. `pki switch` reissues the Pi's certificate from the owner's CA and moves every service to the owner's root, keeping the old one. On a Deevnet Pi the tenant's names, `mqtt`, `logs` and `grafana` under `<tenant>.deevnet.net`, are kept in the owner's certificate. `pki enroll` issues a device's certificate, `pki issuing` makes a new card's CA, and `regen-certs` renews from the owner's CA |
| 3 | **The image carries the tools** ([deevnet-image-factory#38](https://github.com/deevnet/deevnet-image-factory/pull/38)): `deevnet-pki-owner.sh`, `deevnet-pki-media.sh` and the owner's profile, with `cryptsetup-bin`. Not yet built on a released kit, nor in the tenant downloads |
| 2 | In part. `deevnet-kit cert request` makes a key and a request on the Pi; `cert install FULLCHAIN ROOT` checks the certificate is for that key, chains to the root given and names `mqtt`, `logs` and `grafana` under `<tenant>.deevnet.net`, then installs it, keeps the card's CA as `card-ca.pem`, maps the names to loopback in `/etc/hosts` and restarts the services (unit tests). No `pki` switch and no `pki init` yet |
| 3 | The image built with v0.15.0; its kit matches the staged binaries by checksum. Not yet in the downloads on `dv02obs001v01`, and not yet booted (as of 2026-10-25) |
| 3 | **In the tenant downloads, 2026-11-04:** pushed to `dv02obs001v01` with rsync, capped at 5 MB/s, with the operator at the router's console. Delta transfer against the 2026-10-18 image sent 435 MB of the 941 MB in 90 seconds, and the router answered all 44 pings during it. Its checksum verifies on `obs`, and `downloads.mobile.deevnet.net` serves it |
| 3 | **Rebuilt on v0.16.0, 2026-11-07:** `deevnet-kit` and `deevnet-log-user` v0.16.0 staged (`make stage-pi`) and pinned ([deevnet-image-factory#37](https://github.com/deevnet/deevnet-image-factory/pull/37)); `make pi-backend` built the image, its two binaries identical to the staged ones, 938 MB, SHA-256 `fc7e9210…14bd2a13`, and `make pi-backend-publish` put it in the Builder's tenant downloads tree, where its checksum verifies. The 2026-10-25 image is kept outside the tree |
| 3 | **In the tenant downloads, 2026-11-07:** only `tenant/pi/` pushed to `dv02obs001v01` with rsync, capped at 1 MB/s, with the role's ownership and modes, no `--delete`, both files renamed into place together, and the operator at the router's console. Delta transfer against the 2026-10-25 image sent 418 MB of the 938 MB in 6 minutes 55 seconds; a watchdog that would have stopped it pinged the router every second, and it answered all 412. The checksum verifies on `obs`, and `downloads.mobile.deevnet.net` serves the new `.sha256` and the image at its new size |
| 3 | **First booted, 2026-10-27:** EdS's home Pi, from EdS's backend image built on this `pi-backend` (2026-10-26). The card came up on its own CA, as designed |
| 2 | **First used, 2026-10-29** (EdS [CHG-0042](https://cdeever.github.io/eds/docs/changes/2026/0042-the-home-pi-becomes-a-deevnet-pi/)): `cert request` on the Pi, the request signed by eds's `deevnet_certificate`, `cert install` with the full chain and the Root. It checked the key and the chain, said "installed", made the Pi a Deevnet Pi, mapped the names to loopback and restarted the services. `selftest` then passed 13 of 15: Grafana's log data sources still dialed `https://localhost:8427`, which the new certificate does not name, until `deevnet-kit-dashboards` was restarted by hand; then 15 of 15. Three ESP32 devices moved to the Pi's broker on the Root alone |

### Verification on a Pi, 2026-11-08

**V7, V8 and V11 passed** on `dv02rpi004p01`, a Raspberry Pi 4 of the Pi lab, as tenant `mabell`, with a 29 GB USB stick and an ESP32 running MicroPython v1.29.0, whose TLS is mbedTLS. The card was a test image built on the Builder from the merged branches, flashed from the Builder, and never staged or published. The logs are in `migration-logs/chg0056-step2-2026-11-08/` on the Builder.

| Check | Result |
|---|---|
| Step 3's | The card's first boot came up as `mabell` on its own CA, and `selftest` passed all 15 checks once Grafana was restarted (follow-ups) |
| V7 | `cert request` on the Pi, and the request carried to the Builder. The API refused it with no token and with a forged `mabell` token (401), and issued it with `mabell`'s own token (201): for the request's key, naming `mqtt`, `logs` and `grafana` site-less and at `mobile`, for a year. `cert install` made the Pi a Deevnet Pi, and `selftest` passed. A second request, with a new key, renewed it the same way, and the broker served the new key |
| V8 | The ESP32 published once a second with QoS 1, dialling the Pi's address and verifying `mqtt.mabell.deevnet.net`. `pki init` changed nothing served. The ESP32 was given `trust-bundle.pem` and connected against both roots. `pki switch` restarted the broker on the owner's certificate, and the ESP32 reconnected 4 seconds later with nothing changed. Given the owner's root alone, it connected again. mbedTLS accepted the owner's chain with its non-critical name constraints |
| V11 | The card was wiped and written again, as a lost card. On the new card, `pki issuing` made a new issuing CA (serial `4442AF01…`, the old card's `AA359C91…`) from the root on the stick, which matched its fingerprint. Its broker refused the ESP32 178 times on its own CA. After `pki switch` and the ESP32's account restored with its own password, the ESP32 connected at once, with nothing on it changed, and published |

### Departures from the plan

- **No first-boot switch, for either.** A card starts on its own CA, as every card does. It becomes a
  Deevnet Pi when a certificate is installed, and its owner's when `pki switch` runs; the kit's state
  records which (`pki`). Running `pki init` is the choice of `non-deevnet`, and until then the card's
  first-boot certificate is the placeholder.
- **The owner's profiles are a file of their own**, `deevnet-pki-owner.cnf`, beside
  `deevnet-pki.cnf`. The owner's names come in as environment variables, and OpenSSL refuses a whole
  profile with one unset, so in `deevnet-pki.cnf` they would have stopped Deevnet's own ceremony.
- **A Deevnet Pi keeps its tenant's names on the owner's root.** Planning V8 showed that a device,
  which verifies a name, could not stay connected across `pki switch`: the owner's certificate named
  only `.local`, `localhost`, the owner's domains and addresses, and none of the Deevnet one's. On a
  Deevnet Pi, `pki init` now also permits the owner's CA `<tenant>.deevnet.net`, and `pki switch`
  keeps `mqtt`, `logs` and `grafana` under it, so a device changes only its root, as ADR-0041 §4
  lays out (#51). A new card for such a Pi takes `pki issuing --domain <tenant>.deevnet.net`.
- **Verified before release, on a test image.** The image was built from the merged branches with
  the kit built from them, and #51's kit was copied onto the test card over SSH. V7's request
  travelled by SSH rather than a stick: it is the same public file.
- **The image reached `dv02obs001v01` nine days after it was built.** Copying it there crosses the
  core router's `re0`, as in [INC-0004](/docs/incidents/2026/0004-core-router-lost/) and
  [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/), so it waited for a window
  with the operator at the console. The first card from it, EdS's home Pi, was flashed from the
  Builder.

## Follow-ups

Found on the test Pi, 2026-11-08:

- [ ] **Grafana starts before the clock is set.** A Pi has no clock battery and boots with the base
      image's date, 2025-11-24. Grafana started before NTP corrected it, refused every signed
      plugin, VictoriaLogs' included, as "signature expired", and served no device logs until it
      was restarted. The card's first-boot CA and certificate were dated 2025 too. Every card from
      the image is exposed; Grafana, and first boot's certificates, should wait for time sync.
- [ ] `pki issuing` on a new card says to hand out the trust bundle; its devices already hold the
      owner's root, and the next step is `pki switch`.
- [ ] The API holds V7's certificate for `mabell` (`mqtt`), whose key is on the test card. Delete
      its record when the card is wiped; it cannot be revoked.
- [ ] Step 3: release `deevnet-kit` with `pki`, build the image on it, and push it to the tenant
      downloads; then the [deevnet-kit](/docs/platforms/deevnet-software/deevnet-kit/) page and
      the [take-home image](/docs/runbook/tenant/tenant-to-pi-image/) runbook describe `pki`.

Found on the first Deevnet Pi (EdS CHG-0042):

- [x] `cert install` does not rerun the dashboards step, so Grafana's data sources keep
      `localhost` ([deevnet-provisioning-api#41](https://github.com/deevnet/deevnet-provisioning-api/issues/41)). Fixed in
      [deevnet-provisioning-api#45](https://github.com/deevnet/deevnet-provisioning-api/pull/45), released in v0.16.0, in the tenant downloads' image since 2026-11-07.
- [x] `status` and `selftest` warn on a Deevnet Pi that the certificate names none of its
      addresses, and suggest `regen-certs`, which refuses
      ([deevnet-provisioning-api#42](https://github.com/deevnet/deevnet-provisioning-api/issues/42)). Fixed in
      [deevnet-provisioning-api#45](https://github.com/deevnet/deevnet-provisioning-api/pull/45), released in v0.16.0, in the tenant downloads' image since 2026-11-07.
- [x] The provider's same-key renewal cannot be installed by `cert install`; the documented renewal
      is a new request ([deevnet-provisioning-api#43](https://github.com/deevnet/deevnet-provisioning-api/issues/43)). Fixed in
      [deevnet-provisioning-api#45](https://github.com/deevnet/deevnet-provisioning-api/pull/45), released in v0.16.0, in the tenant downloads' image since 2026-11-07.

