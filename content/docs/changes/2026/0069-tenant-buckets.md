---
title: "CHG-0069: Tenant Buckets"
weight: -69
---

# CHG-0069: Tenant Buckets

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment |
| **Classification** | Routine |
| **Status** | Planned |
| **Window** | None needed: new resources only. The API redeploy is a restart of a few seconds |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API), `dv02obj001v01` (the store), the core router (one rule), `deevnet-tenant-tdemo` |
| **Automation** | `deevnet-provisioning-api` and `terraform-provider-deevnet` releases and `make stage`; `deevnet.mgmt` `site.yml --tags deevnet-api,tenant-state,tenant-downloads`; `deevnet.net` for the zone rule. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Most likely to go wrong: a policy that grants more than one bucket, caught by the verification's refusals before any tenant is told |
| **Related changes** | [CHG-0068](/docs/changes/2026/0068-object-store-vm/) (the store, which this needs), [CHG-0065](/docs/changes/2026/0065-tenant-removal-leftovers/) (tenant removal, which gains buckets) |
| **Related runbooks** | [State Store](/docs/runbook/tenant/services/state-store/); an Object Storage page is written in Step 4 |

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

- [ ] [CHG-0068](/docs/changes/2026/0068-object-store-vm/) complete
- [ ] The API's admin credential on the store holds bucket, quota, lifecycle and bucket-policy actions

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

- [ ] Step 1: the API's bucket and key routes, admission and removal, released
- [ ] Step 2: `deevnet_bucket` and `deevnet_bucket_key`, released and staged
- [ ] Step 3: deployed; the `iot` rule in place
- [ ] Step 4: the Object Storage page, Coming Soon updated, the tdemo example
- [ ] Verification passes from `DVNTM-TD` and the IoT segment
- [ ] ADR-0026 Accepted

## Outcome

*To be written.*

### Departures from the plan

## Follow-ups
