---
title: "CHG-0078: The Take-Home Tool Renamed tenant2backend"
weight: -78
---

# CHG-0078: The Take-Home Tool Renamed tenant2backend

| | |
|---|---|
| **Date** | 2026-11-19 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **In progress** |
| **Window** | 2026-11-19 onward. Built and proven on the Builder and a Pi of the Pi lab; the publish crosses the core router throttled, with the owner present |
| **Site** | mobile |
| **Systems** | The artifact server on the Builder; every take-home image (Pi, virtual machine for amd64 and arm64, OVA, VHDX, ISO); the tenant downloads on `dv02obs001v01` |
| **Automation** | `deevnet-provisioning-api`, `deevnet-image-factory`, and EdS's backend image build |
| **Risk** | Medium. Nothing changes on Deevnet's hosts but the artifact server and the tenant downloads, but every published image is replaced. Most likely to go wrong: a unit or path missed by the rename, caught by the self-test; and the push, which is throttled |
| **Related changes** | [CHG-0074](/docs/changes/2026/0074-take-home-vm-image/), [CHG-0075](/docs/changes/2026/0075-take-home-installer-iso/), [CHG-0076](/docs/changes/2026/0076-take-home-virtualbox-hyper-v/), [CHG-0077](/docs/changes/2026/0077-take-home-utm/) (the images rebuilt), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (tenant downloads) |
| **Related runbooks** | [Take Your Tenant Home](/docs/runbook/tenant/take-it-home/) |

---

## Summary

The take-home backend's management tool, `deevnet-kit`, becomes `tenant2backend`, and its files,
units and group take the noun `backend`, as
[ADR-0045](/docs/architecture/decisions/tenant-model/0045-take-home-tool-owners-name/) proposes.
The app contract keeps Deevnet's names. Every take-home image is rebuilt with the new name and
published again. This is the fifth version of
[Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/).

## Goal

- `tenant2backend` released, with its `backend` files, and `deevnet-kit` kept as an alias that
  says the new name.
- Every image rebuilt with it, each passing the self-test.
- EdS's backend image builds on the new Pi image.
- Every image in the tenant downloads with its sha256, and the docs naming `tenant2backend`.

## Scope

**In scope:**
- **The tool:** the command, `/etc/backend`, `/opt/backend`, the `backend-*` units, the `backend`
  group, `backend.txt` on a Pi card (an old `deevnet-kit.txt` still read), and `backend-ca.pem`.
- **The images:** the Pi image, the virtual machine for amd64 and arm64, the OVA, the VHDX and the
  ISO.
- **EdS:** its backend build accepts the new names.
- **Publish and docs:** every image under `tenant/`, the tenant guide, Deevnet Software and the
  Software Catalog.

**Out of scope:**
- The app contract: `DEEVNET_TENANT`, `X-Deevnet-Partition`, the data source UIDs.
- The log bridge's and the PKI tools' names.
- Backends already flashed: there is no upgrade in place, so they keep `deevnet-kit`.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A path, unit or group still under the old name | Every image | The self-test on every rebuilt image, and a search of the play and the kit for the old name |
| An owner's card set up by the old instructions | A Pi card | `deevnet-kit.txt` is still read, and the alias still works |
| EdS's build checks for the old unit and help | EdS | EdS accepts both names before the new Pi image is published |
| The push hangs the core router | Network | Throttled and detached, with the owner present |

## Prerequisites

- [x] Take-Home Media v1 to v4 (CHG-0074 to CHG-0077)
- [ ] ADR-0045, Proposed

## Procedure

### Step 1: The tool

`tenant2backend` in `deevnet-provisioning-api`: the command, its files and the alias, released and
staged on the artifact server.

### Step 2: The images and EdS

The configuration play installs `tenant2backend`, its units, paths and group, and the alias; every
image target pins the new release. EdS's backend build accepts the new names.

### Step 3: Prove them

Every image rebuilt: the virtual machines and the ISO in qemu on the Builder, the Pi image on a Pi
of the Pi lab. Setup, the self-test every check, and the alias.

### Step 4: Publish

Every image under `tenant/` with its sha256, pushed throttled and detached; the tenant guide,
Deevnet Software and the Software Catalog name `tenant2backend`.

## Verification

- On every rebuilt image, first boot runs `tenant2backend`, every `backend-*` unit is active, and
  `sudo tenant2backend selftest` passes every check.
- `deevnet-kit status` works and says the tool is now `tenant2backend`; a card with only
  `deevnet-kit.txt` takes its settings.
- EdS's backend image builds on the new Pi image.
- The published files' sha256s match the ones built.

## Undo

Publish the previous images again: each is kept on the artifact server until this change closes.
The tool's release is additive.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: `tenant2backend` released, with its alias
- [ ] Step 2: the images and EdS take the new names
- [ ] Step 3: every image proven
- [ ] Step 4: published, and the docs name `tenant2backend`
