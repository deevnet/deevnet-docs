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
| **Status** | **Planned.** |
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
- [ ] The vendor claims checked (Step 1)

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

- [ ] Step 1: the vendor claims checked and recorded
- [ ] Step 2: proven off site
- [ ] Step 3: `deevnet-kit` released and staged
- [ ] Step 4: the image built and staged
- [ ] Step 5: tdemo and the guide updated
- [ ] Verification passes on a Pi of the Pi lab with an Android phone

## Outcome

Not started.
