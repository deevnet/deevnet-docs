---
title: "ADR-0045: The Take-Home Tool's Name"
weight: -45
---

# ADR-0045: The Take-Home Backend's Own Tool Carries the Owner's Name, and the App Contract Keeps Deevnet's

|  |  |
|--|--|
| **Status** | Proposed (2026-11-19) |
| **Date** | 2026-11-19 |
| **Scope** | The names an owner meets on a take-home backend: its management tool, that tool's files, units and group, the settings file on a Pi card, and the backend's CA file. Not the names the app contract shares with Deevnet, and not the log bridge's or the PKI tools' names |
| **Related** | [Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/) v5, [ADR-0044](/docs/architecture/decisions/tenant-model/0044-take-home-media/), [ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/), [Take Your Tenant Home](/docs/runbook/tenant/take-it-home/) |

---

## Context

**A take-home backend belongs to its owner.** Nothing on it is Deevnet's: no account, key or
route, and its CA and secrets are made on it at first boot. Yet the tool that manages it, its files
and its units are named `deevnet-kit`: `sudo deevnet-kit status`, `/etc/deevnet-kit`,
`deevnet-kit-firstboot.service`, `deevnet-kit.txt` on a Pi card, `deevnet-kit-ca.pem` on every
device. An owner reading those names is told the backend is Deevnet's.

**Some Deevnet names on the backend are the app contract.** `DEEVNET_TENANT`, the
`X-Deevnet-Partition` header and the dashboards' data source UIDs are the same on Deevnet and on
the backend, which is what lets an app move with one `kit.env` and dashboards apply to both
unchanged.

**There is no upgrade in place.** A backend runs what its image carried; a new name reaches new
images only.

## Decision

### 1. The tool is `tenant2backend`

**The take-home backend's management tool is named `tenant2backend`.** Every subcommand configures
or checks the backend: setup, accounts, buckets, alerts, certificates, its PKI, the self-test and
the export. The name says what the move makes of a tenant, and names no brand.

### 2. Its files take the noun `backend`

**The tool's files, units and group are named for what they are, the backend:** `/etc/backend`,
`/opt/backend`, the `backend-*` systemd units, the `backend` group, `backend.txt` on a Pi card's
boot partition, and `backend-ca.pem`, the backend's own CA as devices receive it.

### 3. The app contract keeps Deevnet's names

**Every name the app contract shares with Deevnet stays as it is**: `DEEVNET_TENANT`, the
`X-Deevnet-Partition` header, the `deevnet-*` data source UIDs, the topic prefix and the reserved
`log` level. An app moves with one `kit.env`, and a dashboard applies to Deevnet and to the backend
unchanged.

### 4. The old name stays for one release

**On the first images with the new name, `deevnet-kit` still works**, as an alias that says the
tool is now `tenant2backend`, and a card's `deevnet-kit.txt` is still read. The alias is removed in
the release after. Backends flashed before the rename keep `deevnet-kit`.

## Consequences

- Every take-home image is rebuilt and published again with the new name.
- EdS, whose backend image builds on the Pi image and checks for the kit's units and help, accepts
  the new names before the new Pi image is published.
- Records and decisions written before this one keep `deevnet-kit`: they describe what was.
- The tenant guide and Deevnet Software name `tenant2backend`, with a note that older images say
  `deevnet-kit`.
- The log bridge (`deevnet-log-bridge`) and the PKI tools (`deevnet-pki-*`) still carry Deevnet's
  name on the backend; whether they follow is a later choice.

## Alternatives considered

- **`setup-tenant` or `setup-backend`.** Close, but "setup" reads as a one-time step, and the tool
  stays the backend's control for its whole life. "Tenant" alone is Deevnet's word for what an
  owner had on the site.
- **`configure-backend`.** Accurate, and was the other name the owner considered.
- **A control-tool name (`backendctl`).** It suggests a daemon controller, which the tool is not.
- **Renaming the contract too.** It would make an app's settings differ between Deevnet and the
  backend, which breaks the one-file move.
- **A clean break, with no alias.** EdS's build and every instruction would have to change at the
  same moment as the images.

## To accept

- [ ] Built by a change record: the tool renamed, every image rebuilt with it
- [ ] Every rebuilt image passes the self-test, and the `deevnet-kit` alias works
- [ ] EdS's backend image builds on the new Pi image
- [ ] Every image in the tenant downloads, and the docs name `tenant2backend`
