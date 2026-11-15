---
title: "CHG-0073: Buckets on the Take-Home Pi"
weight: -73
---

# CHG-0073: Buckets on the Take-Home Pi

| | |
|---|---|
| **Date** | 2026-11-15 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **Planned.** |
| **Window** | Unscheduled. A silo build for arm64, a `deevnet-kit` release and an image build, possibly shared with [CHG-0072](/docs/changes/2026/0072-pi-metrics-and-alerting/) |
| **Site** | mobile |
| **Systems** | `deevnet-kit`; silo, built for arm64; the take-home image; the tenant downloads on `dv02obs001v01`; `deevnet-tenant-tdemo`; one Pi of the Pi lab for the test |
| **Automation** | `deevnet-container-image-factory` (silo), `deevnet-provisioning-api` (`cmd/deevnet-kit`), `deevnet-image-factory` `make pi-backend` |
| **Risk** | Medium. Most likely to go wrong: silo's memory on a small Pi. It stays off until the first bucket, and is capped |
| **Related changes** | [CHG-0069](/docs/changes/2026/0069-tenant-buckets/) (buckets on Deevnet), [CHG-0068](/docs/changes/2026/0068-object-store-vm/) (silo), [CHG-0072](/docs/changes/2026/0072-pi-metrics-and-alerting/) |
| **Related runbooks** | [Convert a Tenant to a Pi Image](/docs/runbook/tenant/tenant-to-pi-image/), [Object Storage](/docs/runbook/tenant/services/object-storage/) |

---

## Summary

A tenant's app can keep its data in a Deevnet bucket (CHG-0069). On the take-home Pi it has none.
This change gives the Pi a small bucket store of its own: **silo, the software that serves Deevnet's
buckets**, built for arm64 and run on the card, with the same bucket rules. `deevnet-kit` gains
commands that make buckets and keys through the API's own bucket code, and a key from the tenant's
Terraform can be brought along, so the app's settings carry over.

## Goal

- An app that reads and writes a Deevnet bucket does the same on the Pi, with the same bucket name
  and, if the owner brings it, the same key.
- A key reaches only its own bucket, and a read key cannot write.
- A Pi with no buckets runs no bucket store.

## Scope

**In scope:**
- **silo for arm64:** built in `deevnet-container-image-factory` from the tag Deevnet runs, and
  staged as a binary.
- **`deevnet-kit`:**
  - `bucket add`, `bucket list`, `bucket rm`, `bucket key add`, `bucket key list`, `bucket key rm`,
    with the quota, versioning, expiry and anonymous read Deevnet's buckets have;
  - `--key-file` to adopt a key from `terraform output -json`;
  - `S3_ENDPOINT` and `S3_CA_FILE` in `kit.env`, and `export --bucket` for one key's lines;
  - `s3` among the card's TLS names; self-test checks once a bucket exists.
- **The image:** silo, disabled until the first bucket, on port 9000 with the card's certificate.
- **tdemo:** the bucket lines in `kit_env`.
- **The guide:** a Buckets step, and copying objects from Deevnet.

**Out of scope:**
- Copying objects: the owner's, with `rclone` or `mc`, as the guide shows.
- Runtime secrets.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| silo crowds out the other services | The Pi | Off until the first bucket; `MemoryMax`; measured on a real Pi |
| A key reaches another bucket | The Pi | The API's own key policies; the self-test tries it |
| Quotas exceed the card | The Pi | The kit refuses a quota the disk can't hold |
| The arm64 build differs from Deevnet's silo | Supply | Built from the same tag, with the same build stage |

## Prerequisites

- [x] Buckets built and proven on Deevnet (CHG-0069)
- [ ] The vendor claims checked (Step 1)

## Procedure

### Step 1: Check the vendor claims

- silo builds for arm64 from the tag Deevnet runs.
- On a single drive it supports versioning, bucket quotas and lifecycle expiry, as on Deevnet.
- It serves TLS from a certificate directory, and picks up a renewed certificate.
- Its idle memory.

### Step 2: Prove it off site

On the Builder, in a Debian container: `deevnet-kit bucket add`, `key add` with and without
`--key-file`, then an app's reads and writes with each key, and the refusals.

### Step 3: The build and the kit

The silo arm64 build; the bucket commands in a `deevnet-kit` release.

### Step 4: The image

silo and its unit in `make pi-backend`. Stage the image.

### Step 5: tdemo and the guide

## Verification

On a Pi of the Pi lab:
- `deevnet-kit bucket add` starts the store, and `selftest` passes.
- An app with the exported `kit.env` writes and reads its bucket with a write key.
- A read key is refused a write, and every key is refused another bucket.
- A key adopted from tdemo's Terraform output works unchanged.
- A bucket with `public_read` serves an object with no key; listing it still needs one.
- Memory with the store running is recorded.

## Undo

Flash the previous image. Buckets made on the Pi are lost with its card; copy them off first.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: the vendor claims checked and recorded
- [ ] Step 2: proven off site
- [ ] Step 3: silo for arm64 built and staged; `deevnet-kit` released
- [ ] Step 4: the image built and staged
- [ ] Step 5: tdemo and the guide updated
- [ ] Verification passes on a Pi of the Pi lab

## Outcome

Not started.
