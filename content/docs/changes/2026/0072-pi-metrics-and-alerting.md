---
title: "CHG-0072: Metrics and Alerting on the Take-Home Pi"
weight: -72
---

# CHG-0072: Metrics and Alerting on the Take-Home Pi

| | |
|---|---|
| **Date** | 2026-11-15 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Complete** (2026-11-16). A real Pi passes every self-test check, and an alert exported from Terraform fires and resolves on it. Delivery to a phone is left unverified, by the owner's choice |
| **Window** | Unscheduled. One `deevnet-kit` release, one image build, the image staged to the tenant downloads |
| **Site** | mobile |
| **Systems** | `deevnet-kit` and `deevnet-log-user`; the take-home image `raspios-bookworm-mobile-pi-backend.img.xz`; the tenant downloads on `dv02obs001v01`; `deevnet-tenant-tdemo`; one Pi of the Pi lab for the test |
| **Automation** | `deevnet-provisioning-api` (`cmd/deevnet-kit`), `deevnet-image-factory` `make pi-backend` |
| **Risk** | Medium. Most likely to go wrong: the Pi runs out of memory. Each new component is capped, and the guide states what each Pi model can run |
| **Related changes** | [CHG-0070](/docs/changes/2026/0070-tenant-metrics-store/) and [CHG-0071](/docs/changes/2026/0071-tenant-alerting/) (the services this brings to the Pi), [CHG-0056](/docs/changes/2026/0056-kit-deevnet-or-own-pki/) (the image this replaces), [CHG-0073](/docs/changes/2026/0073-pi-buckets/) (buckets on the Pi) |
| **Related runbooks** | [Convert a Tenant to a Pi Image](/docs/runbook/tenant/tenant-to-pi-image/) |

---

## Summary

The take-home Pi keeps a tenant's app contract when the app leaves Deevnet: the same ports, topics,
tokens and Grafana data sources, on a Pi of the owner's own. It was built when Deevnet offered MQTT,
logs and log dashboards. Deevnet has since added metrics (CHG-0070) and alerting (CHG-0071), and an
app that uses them loses them on the Pi; tdemo's `kit_env` already names `METRICS_ENDPOINT`, which
the Pi doesn't provide.

This change brings both to the Pi, built from Deevnet's own pieces:
- **Metrics:** the same VictoriaMetrics cluster, behind the Pi's vmauth, written and read with the
  Pi's log tokens. `METRICS_ENDPOINT` joins the Pi's `kit.env`, and Grafana gains the metrics data
  source.
- **Alerting:** vmalert, Alertmanager and ntfy on the Pi. **The tenant's rules come from its own
  Terraform**, exported as JSON and imported with `deevnet-kit alerts import`, which hands them to
  the same writer code the API uses. The owner's phone reads its alerts on the Pi's network.
- **The guide** is brought up to date.

## Goal

- An app that runs on Deevnet with tdemo's `kit_env` runs on the Pi with the Pi's `kit.env`,
  metrics and all, unchanged.
- The tenant's alert rules, exported from its Terraform, load on the Pi unchanged, and are refused
  there for the same reasons the API refuses them.
- A rule over metrics and a rule over device logs each fire and reach an Android phone on the Pi's
  network, and each sends a resolved notification.
- A Pi with 2 GB or more runs everything; the guide says what a smaller Pi runs.

## Scope

**In scope:**
- **`deevnet-kit`** (with `deevnet-log-user`, which shares its tag):
  - the metrics store's settings in the writer's base file, so the writer renders the metrics routes
    it renders on Deevnet, unchanged;
  - `alerts import`, `alerts list`, `alerts clear` and `notify`;
  - the ntfy login and the publisher's password, made on the card;
  - `METRICS_ENDPOINT` and `NOTIFY_*` in `kit.env`, and the metrics data source in Grafana;
  - `metrics` and `ntfy` among the card's TLS names;
  - self-test checks for each new service.
- **The image:** vmstorage, vminsert and vmselect; vmalert, Alertmanager and ntfy; vmauth's loopback
  listener for vmalert; the sync unit that starts and stops vmalert.
- **tdemo:** an `alert_rules` output, and `NOTIFY_*` in `kit_env`.
- **The guide:** the ports, the env table, "Bring your alert rules", "Your phone", what does not
  come along, and memory by Pi model.

**Out of scope:**
- Buckets: [CHG-0073](/docs/changes/2026/0073-pi-buckets/).
- Runtime secrets, which stay off the Pi, as before.
- Alerts away from the Pi's network: a future ADR, with off-site delivery for the home site.
- A provider change: the export is a Terraform output.
- The "one pattern from tenant to Pi" ADR, parked.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The Pi runs out of memory | The Pi | Each new component capped (`-memory.allowedBytes`, `MemoryMax`); measured on a real Pi; the guide's memory by model |
| The kit and the writer disagree on the alerts request | `deevnet-kit`, `deevnet-log-user` | One tag for both, pinned together in the image; a writer test pins the Pi's configuration |
| A Deevnet Pi's certificate, issued before this release, lacks `metrics` and `ntfy` | The Pi | `status` warns and says how to renew; the guide says so |
| The vmauth upgrade breaks the log path | The Pi | The existing log self-tests |
| The SD card fills | The Pi | Retention chosen in Step 1; free-space checks in `status` |

## Prerequisites

- [x] Metrics and alerting built and proven on Deevnet (CHG-0070, CHG-0071)
- [x] The vendor claims checked (Step 1)

## Procedure

### Step 1: Check the vendor claims

- vmauth `v1.156.0` takes a third listener, plain HTTP on loopback, with its internal routes still on
  their own loopback port.
- The arm64 releases carry `vmalert-prod`, `vmauth-prod` and the three cluster binaries at
  `v1.156.0`; Alertmanager `v0.35.0` and ntfy `v2.38.0` have arm64 builds.
- Alertmanager runs with gossip off and reads its webhook password from a file.
- ntfy serves TLS on 443 and plain HTTP on loopback in one process.
- Android resolves `<hostname>.local` in the ntfy app, or the guide gives the Pi's address, which its
  certificate already names.
- `terraform output -json alert_rules` decodes into the writer's alerts request with unknown fields
  refused.
- Metrics retention on an SD card: 90 days, as on Deevnet, or 30, as the Pi's logs.

### Step 2: Prove it off site

On the Builder, in a Debian container, with the amd64 builds of the same versions and the image's
unit flags: `deevnet-kit init`, an import of tdemo's exported rules, then `selftest`. A rule that
always fires reaches the tenant's topic as the tenant's ntfy login. Measure each component's
memory.

### Step 3: The kit

`deevnet-provisioning-api` `v0.26.0`, with the CHANGELOG and `make stage-pi`.

### Step 4: The image

`deevnet-image-factory`: the new binaries and units, and `make pi-backend`. Stage the image to the
tenant downloads.

### Step 5: tdemo and the guide

The `alert_rules` output and `kit_env` lines; the guide's new steps and tables.

## Verification

On a Pi of the Pi lab, flashed with the new image:
- `deevnet-kit selftest` passes every check.
- An app with the exported `kit.env` pushes a metric and reads it back, and it shows in Grafana
  through `deevnet-metrics-workloads`.
- tdemo's exported rules import. A rule labeled `tenant`, and one vmalert won't load, are refused.
- A metrics rule and a device-log rule each fire and reach an Android phone on the Pi's network,
  and the metrics rule sends a resolved notification.
- The ntfy login is refused a publish.
- After `deevnet-kit cert install`, each service still answers by name.
- Memory, by component, is recorded.

## Undo

Flash the previous image (CHG-0056's). Nothing on Deevnet changes.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the vendor claims checked and recorded
- [x] Step 2: proven off site
- [x] Step 3: `deevnet-kit` released and staged
- [x] Step 4: the image built and staged
- [x] The image rebuilt with the alerting unit's boot-order fix ([deevnet-image-factory#45](https://github.com/deevnet/deevnet-image-factory/pull/45))
- [x] Step 5: tdemo and the guide updated
- [x] Verification passes on a Pi of the Pi lab (the phone left unverified, by the owner's choice)

## Outcome

### Step 1: the vendor claims (2026-11-15)

Checked against the release files and by running the arm64 binaries themselves, under qemu on the
Builder.

| Claim | Found | Holds |
|---|---|---|
| The arm64 releases | `vmutils-linux-arm64-v1.156.0` carries `vmauth-prod` and `vmalert-prod`; `victoria-metrics-linux-arm64-v1.156.0-cluster` carries `vmstorage-prod`, `vminsert-prod` and `vmselect-prod`; Alertmanager `0.35.0` and ntfy `2.38.0` publish `linux-arm64` builds. Each matches its release's checksum | Yes |
| vmauth takes a third listener | `-httpListenAddr=0.0.0.0:8427,127.0.0.1:8428,` with `-tls=true,false,false` and `-httpInternalListenAddr=,,127.0.0.1:8426`: 8428 serves the same users in plain HTTP; `/-/reload` answers 401 there and on 8427, and 200 only on 8426 | Yes |
| Alertmanager with gossip off | `--cluster.listen-address=` empty: it starts, is ready, and delivers with `basic_auth.password_file` naming a host path | Yes |
| ntfy on 443 and loopback at once | `NTFY_LISTEN_HTTPS=:443` with the card's certificate and `NTFY_LISTEN_HTTP=127.0.0.1:2586` in one process: both answer `/v1/health` | Yes |
| The Terraform export | The same `for` expressions as tdemo's `alert_rules` output, applied, print JSON (`"for": null` and `"labels": null` where unset) that the kit's strict decoder reads | Yes |
| Retention on an SD card | Decided: **30 days**, as the Pi's logs, not Deevnet's 90 | — |
| Android resolves `<hostname>.local` | Left to the verification, on a real phone | Open |

### Step 2: proven on the Builder (2026-11-15)

The Pi's stack in a `debian:bookworm` container, with the Pi's arm64 binaries under qemu: the
metrics cluster, VictoriaLogs, vmauth with the three listeners, Alertmanager, ntfy on 443, and the
new `deevnet-kit` and `deevnet-log-user`, with the image's writer configuration. Only the steps
systemd takes on a Pi were done by hand: starting the services, and the sync script's work.

- **`deevnet-kit init`** made the phone's login and the publisher's password, and the writer
  rendered Deevnet's metrics routes from the kit's base file, unchanged.
- **Metrics:** the ingest token pushed, the read token was refused a write, and a write to another
  tenant's partition was refused.
- **The import:** the rules, as Terraform exports them, loaded. A rule labeled `tenant` was refused
  by the kit before the writer was asked, and a rule vmalert won't load was refused with vmalert's
  reason.
- **ntfy:** the tenant's login read its topic, and was refused a publish (403); anonymous was
  refused.
- **Both alerts**, over a metric and over a log line, **reached `tdemo-chg0072`**, and vmalert
  reported no rule error.
- **`deevnet-kit selftest`:** every new check passed: TLS on 443, metrics in and out, another
  partition refused, Alertmanager ready, the login's two rights. The checks of services that need
  systemd, Mosquitto or Grafana could not pass in the container.
- **Memory** under qemu, which overstates a real Pi: ntfy 101 MB, Alertmanager 84, vmstorage 54,
  vmselect 47, vmalert 46, vminsert 35. Measured again on a real Pi.

**The kit and the image are written:**
[deevnet-provisioning-api#78](https://github.com/deevnet/deevnet-provisioning-api/pull/78) (the
kit), [deevnet-image-factory#43](https://github.com/deevnet/deevnet-image-factory/pull/43) (the
image) and [deevnet-tenant-tdemo#22](https://github.com/deevnet/deevnet-tenant-tdemo/pull/22) (the
export).

### Step 3: the kit released (2026-11-16)

**`deevnet-provisioning-api` v0.26.0 carries the kit and the writer the image installs.** The
kit's metrics and alerting
([deevnet-provisioning-api#78](https://github.com/deevnet/deevnet-provisioning-api/pull/78)) and
its buckets ([#79](https://github.com/deevnet/deevnet-provisioning-api/pull/79)) were released
together, and `make stage-pi` put both arm64 binaries on the Builder's artifact server. Deevnet's
own API and writer stay at v0.25.0: nothing in this release changes them.

### Step 4: the image built and staged (2026-11-16)

**The new image is what the tenant downloads serve.** The upstream arm64 releases were staged from
the copies checked in Step 1, against the checksums the image factory pins, rather than downloaded
again. `make pi-backend` built the image with the config play's 46 tasks and no failure. Mounted
read-only, it holds every new binary and unit, with the metrics cluster, Alertmanager, ntfy and the
alerting units enabled, silo installed but off, and no `a_autoprov`.

**The push to the tenant downloads crossed the core router at 1 MB/s, with the router watched.**
rsync sent 568 MB of the 1.06 GB image as a delta against the previous one, in about 9 minutes; the
router answered all 555 pings. The checksum on `dv02obs001v01` matches the Builder's.

### Step 5: tdemo and the guide (2026-11-16)

**tdemo exports its alert rules, and the guide tells a tenant how to bring them.** tdemo's
`alert_rules` output and `kit_env` lines ([deevnet-tenant-tdemo#22](https://github.com/deevnet/deevnet-tenant-tdemo/pull/22))
and the guide's new steps ([deevnet-docs#446](https://github.com/deevnet/deevnet-docs/pull/446)) are merged.
The guide now states what the real Pi showed: memory, the self-test's checks, and what is not yet tried
on hardware.

### Verification (2026-11-16)

**On `dv02rpi004p01` in the Pi lab, the image boots as tdemo and every self-test check passes
after one fix by hand.** The card was flashed on the Builder and read back to the image's checksum;
the owner's login, host name and tenant were set on its boot partition, as a tenant would set them.

- **On the first boot, 24 of 27 checks passed.** `deevnet-kit-alerting` ran when vmauth's process
  had started but before vmauth listened, so the writer's closing reload of vmauth was refused. The
  phone's ntfy login was therefore never made, and ntfy answered the self-test 401 rather than 403.
  Restarting the unit by hand made it, and **27 of 27 passed**: TLS on all four ports, logs and
  metrics in and out, another tenant's partition refused, Grafana, Alertmanager, and the ntfy
  login's two rights. [deevnet-image-factory#45](https://github.com/deevnet/deevnet-image-factory/pull/45)
  makes the unit retry for up to two minutes; the image is rebuilt with it.
- **tdemo's rules export from Terraform** after an apply that created its two rule groups and its
  ntfy login on Deevnet. A refresh-only apply cannot do it: the state predates alerting.
- **The rules import on the Pi**, and `alerts list` shows both groups. `backend_queue_depth` held
  at 150 for seven minutes fired `QueueBacklog` at 17:53 UTC, and it resolved at 17:59, a minute
  after the pushes stopped. Both messages were read back from the Pi's ntfy with the phone's login:
  rule, vmalert, Alertmanager and ntfy, end to end.
- **Memory:** with everything running, the bucket store included, the Pi uses about 815 MB.
- **The image is rebuilt with #45 and staged again** (sha256 `caff440adecb8c395c5b72fae056f84de5601b84777f8b87f6a0a20c8587479a`), served by the tenant downloads.
- **Left unverified, by the owner's choice:** an alert arriving on a phone, Android's `.local`
  resolution, and `cert install` on a Deevnet Pi. The lab's Pi is on the IoT VLAN, which the tenant
  Wi-Fi cannot reach by design, so the phone needs the Pi moved to a flat network. The alert path up
  to ntfy is proven; what remains is the phone's own subscription.
- **An alert's "Source" link** points at vmalert on an internal port the phone can't open. The
  message carries the alert's name, status and summary; the guide says so.