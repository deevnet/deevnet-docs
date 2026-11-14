---
title: "CHG-0069: Tenant Buckets"
weight: -69
---

# CHG-0069: Tenant Buckets

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | In Progress. Deployed and verified from the Builder on 2026-11-14: API v0.23.0, provider v0.11.0. Open: a public read from a device on the IoT segment and a check from `DVNTM-TD`, and ADR-0026's acceptance, which waits on CHG-0068 |
| **Window** | None needed: new resources only. The API redeploy is a restart of a few seconds |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API), `dv02obj001v01` (the store), the core router (one rule), `deevnet-tenant-tdemo` |
| **Automation** | `deevnet-provisioning-api` and `terraform-provider-deevnet` releases and `make stage`; `deevnet.mgmt` `site.yml --tags deevnet-api,tenant-state,tenant-downloads`; `deevnet.net` for the zone rule. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Most likely to go wrong: a policy that grants more than one bucket, caught by the verification's refusals before any tenant is told |
| **Related changes** | [CHG-0068](/docs/changes/2026/0068-object-store-vm/) (the store, which this needs), [CHG-0065](/docs/changes/2026/0065-tenant-removal-leftovers/) (tenant removal, which gains buckets) |
| **Related runbooks** | [Object Storage](/docs/runbook/tenant/services/object-storage/) |

---

## Summary

After [CHG-0068](/docs/changes/2026/0068-object-store-vm/), the object store on `dv02obj001v01`
holds only Terraform state. [ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/)
§3 gives tenants buckets of their own in it. This change makes them declarable through the
Deevnet API and the provider:
- A `deevnet_bucket` has a hard quota, optional versioning, lifecycle rules, and site-only anonymous
  read.
- A `deevnet_bucket_key` gives a bucket further keys, read-write or read-only.

## Goal

- A tenant declares `deevnet_bucket` and `deevnet_bucket_key` in its Terraform. The store then
  holds bucket `<tenant>-<name>` with the declared quota, versioning, lifecycle and anonymous read.
  Each key reaches that bucket only.
- The API refuses a bucket whose quota would take the sum of all quotas past the store's capacity
  minus the 5 GB state reserve.
- Removing a tenant removes its buckets, their contents and their keys.
- The tenant runbook has an Object Storage page, and Coming Soon loses its entry.

## Scope

**In scope:**
- The API's bucket and bucket-key routes, and their MinIO-admin backend.
- Capacity admission.
- Tenant removal.
- The provider's two resources.
- One zone rule for devices.
- The tenant docs and a tdemo example.

**Out of scope:**
- Serving objects to the internet (ADR-0026 §5).
- Backing up tenant buckets (§4).
- Presigned URLs, which work already, with any key.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A key or anonymous policy reaches more than its bucket | the store | Verification refuses each one across buckets and tenants, and refuses anonymous listing |
| Quotas overcommit the disk | the store | Admission in the API, from configured capacity and reserve; checked by a refused create |
| A quota misses noncurrent versions | the store | Verification writes past the quota by overwriting a versioned object |
| Devices gain more than the store | the core router | One rule: `iot` to `dv02obj001v01`, 443 only. Every bucket but a `public_read` one needs a key |

## Prerequisites

- [x] [CHG-0068](/docs/changes/2026/0068-object-store-vm/)'s store built (Steps 1 to 9; the record stays open for two tenants' plans)
- [x] The API's admin credential on the store holds bucket, quota, lifecycle and bucket-policy actions

## Procedure

### Step 1: The API

- A bucket store, beside the state store's interface, implemented in the MinIO backend
  (`internal/backend/minio`). It covers:
  - creating `<tenant>-<name>`;
  - its hard quota;
  - versioning;
  - lifecycle rules (current-object and noncurrent-version expiry);
  - an anonymous `GetObject` bucket policy for `public_read`;
  - keys as users with a policy confined to one bucket, read-write or read-only.
- Routes for buckets and bucket keys. Secrets are returned in create responses only.
- Capacity admission: configured capacity (100 GB) minus the reserve (5 GB) against the sum of all
  quotas.
- Tenant removal empties and deletes the tenant's buckets and removes their keys.
- Release, with the CHANGELOG.

### Step 2: The provider

- `deevnet_bucket`: `name`, `quota_gb` (required), `versioning`, a `lifecycle` block
  (`expire_days`, `noncurrent_expire_days`) and `public_read`. Exported: the bucket's full name, the
  endpoint, and one read-write key.
- `deevnet_bucket_key`: `bucket` and `access` (`read` or `write`).
- Release, with the CHANGELOG and the provider's docs site, and stage it in tenant downloads.

### Step 3: Deploy

Grant the API's admin credential the new actions in the store role. Deploy the API, then add the
zone rule `iot -> dv02obj001v01` on 443.

### Step 4: Docs and the reference tenant

- **The tenant runbook:**
  - A new page, `runbook/tenant/services/object-storage.md`. It states that the substrate stores and
    does not back up a bucket's contents.
  - Coming Soon loses Object Storage.
- **`deevnet-tenant-tdemo`** gets an example bucket.
- **Platform docs:** the Deevnet API's page and the provider's docs gain the resources.

## Verification

From `DVNTM-TD`, with tdemo:
- Create a bucket with a 1 GB quota and versioning on.
- Put and get with its key.
- A `read` key gets and is refused a put.
- A write past the quota fails at once, including by overwriting a versioned object.
- The lifecycle rule reads back as declared.
- A `public_read` bucket answers a GET with no key, from `DVNTM-TD` and from the IoT segment.
- Anonymous listing is refused.
- A bucket without `public_read` refuses an anonymous GET.
- Another tenant's key is refused the bucket.
- A bucket whose quota exceeds the remaining capacity is refused at create.
- `terraform destroy` removes the bucket and its keys.
- A scratch tenant with a bucket is removed, and nothing of it is left on the store.

## Undo

### Undo Step 3

Redeploy the previous API release and remove the zone rule. Buckets already created stay on the
store until removed by hand.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the API's bucket and key routes, admission and removal, released
- [x] Step 2: `deevnet_bucket` and `deevnet_bucket_key`, released and staged
- [x] Step 3: deployed; the `iot` rule in place
- [x] Step 4: the Object Storage page, Coming Soon updated, the tdemo example
- [x] Verification passes from the Builder
- [ ] A check from `DVNTM-TD`, and a public read from a device on the IoT segment
- [ ] ADR-0026 Accepted

## Outcome

**Tenants declare buckets and keys in their Terraform, and the bucket store on `dv02obj001v01`
holds them.** Deployed on 2026-11-14: Deevnet API v0.23.0 and provider v0.11.0.

- **Step 1:** the API's routes, admission against the bucket store's capacity, reconcile and
  removal, and a sealed copy of each key's secret. Unit tests cover the service, and integration
  tests cover the store calls against MinIO and the registry against PostgreSQL.
- **Step 2:** `deevnet_bucket` and `deevnet_bucket_key`. Tested with real Terraform against a fake
  of the contract.
- **Step 3:**
  - The API's `deevnet-api` user on the bucket store, with the same credential as on the state
    store, holds user, policy and bucket administration, and nothing that reads or writes an object.
    Proven 14 of 14 as that user.
  - The core router added `iot -> object store (https)`, one rule, nothing else changed.
- **Step 4:** the Object Storage page, Coming Soon without it, and tdemo's `files` bucket with a
  read-only key, applied and re-planned clean.
- **Verification, from the Builder, as tdemo:**
  - Read-write and read-only keys each did what their access says.
  - Each key was refused the other bucket.
  - A `public_read` bucket answered an anonymous GET, and refused anonymous listing and PUT; a
    private bucket refused an anonymous GET.
  - A bucket past the remaining capacity was refused with 409: *"the bucket store has 98 GB of 100
    GB left to allocate; this needs 100 GB"*.
  - The quota, versioning and lifecycle read back as declared.
  - `force_destroy` emptied and removed a bucket holding 1.2 GB, with its key.

### Departures from the plan

- **A multipart upload is counted after it completes.** On the store itself, a 1.2 GB object sent
  multipart was accepted against a 1 GiB quota, and the next small write was refused 15 seconds
  later. Only a single-part upload larger than the quota is refused at once. ADR-0026, the tenant
  page, the provider's and the API's docs, and the smoke test say so.
- **No 5 GB reserve in the admission.** CHG-0068 put Terraform state on a disk of its own, so the
  API admits against the bucket store's whole 100 GB.
- **The lifecycle block is `object_lifecycle`.** Terraform reserves `lifecycle` in every resource.
- **The checks ran from the Builder**, on management, not from `DVNTM-TD`, and the IoT segment was
  not reachable from it to test a device's read.
- **Removing a tenant with buckets** is covered by the API's tests, not exercised on the site.

## Follow-ups

- A check from `DVNTM-TD`, and a public read from a device on the IoT segment.
