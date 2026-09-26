---
title: "ADR-0026: Object Storage"
weight: 26
---

# ADR-0026: The State Store Becomes Object Storage, Defined by a Contract, With State and Tenant Buckets as Two Classes

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-21 |
| **Scope** | What the substrate's S3 service must guarantee, which engine provides it, and how it serves both Terraform state and tenants' own buckets. Covers isolation, quotas, locking, versioning, transport and replication. |
| **Extends** | [ADR-0007: Terraform State Custody](/docs/architecture/decisions/0007-terraform-state-custody/), which offered a state store and chose MinIO as a detail; [ADR-0014: Tenant State Durability](/docs/architecture/decisions/0014-tenant-state-durability/), whose data disk and replica this store needs before it holds anything more |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/0010-tenants-consume-platform-services/) §4, [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/) §6, [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/0016-substrate-secrets-openbao/) |

---

## Context

### The engine under the state store is abandoned

- **The state store is MinIO's community edition, `RELEASE.2025-09-07`**, on `dv02prv001v01`.
- **The API confines each tenant through MinIO's own admin API.** It creates a user per tenant with a
  canned policy limiting it to that tenant's prefix of one bucket, `tf-state`.
- **Tenants lock state with `use_lockfile = true`.**

MinIO's community repository was archived on 2026-04-25:
- It says *"THIS REPOSITORY IS NO LONGER MAINTAINED"*.
- *"The MinIO community edition is now distributed as source code only. We will no longer provide
  pre-compiled binary releases."*
- The site's release predates the last published one, `RELEASE.2025-10-15`, which fixed *"Privilege
  Escalation via Session Policy Bypass in Service Accounts and STS"*. The API creates plain users,
  not service accounts, but a store that will receive no further fixes is the real problem.

MinIO's commercial successor, AIStor Free, doesn't fit this site:
- It is proprietary, and licensed *"solely in standalone mode"*.
- It *"requires an active and unexpired MinIO Software License"*, which it renews online. A site
  that is sometimes offline can't depend on that.

### The store doesn't serve TLS, whatever ADR-0016 says

- ADR-0016 lists the state store among the services the site CA issues certificates to.
- The `minio` role configures no TLS, and both tenants' backends point at
  `http://tfstate.mobile.deevnet.net:9000`.
- Tenant state holds secrets: API tokens and broker passwords (ADR-0012 §4). They travel in the
  clear on tenant transit and Platform.

This record fixes that. It is recorded here because the replacement is where the fix lands.

### What is wanted: storage in the spirit of cloud

Terraform state is one use of object storage. A tenant's application wants the same thing a cloud
tenant gets:
- buckets of its own
- a key that reaches only those buckets
- a quota

Treating the store as **object storage**, with state as one of its uses, gives tenants that and keeps
state durable.

### What Terraform's locking actually requires

- Terraform's documentation says only that `use_lockfile` is *"Whether to use a lockfile for locking
  the state file"*, and that support for S3-compatible stores is *"'best effort'"*.
- The change that introduced it states the mechanism: *"If an object with the same key name already
  exists, the write operation fails with a 412 Precondition Failed response."*
- **So a store is usable for state only if a second `PutObject` with `If-None-Match: *` fails
  atomically with 412, including on a versioned bucket.**

---

## Options considered

Vendor documentation and repositories were checked on 2026-09-21.

| | Conditional writes (`use_lockfile`) | Versioning | Tenant isolation | Hard quotas | Replication | License | Weight | Verdict |
|---|---|---|---|---|---|---|---|---|
| **MinIO community, as is** | yes | yes | IAM policies | yes | yes | AGPLv3 | small | Rejected: archived, no fixes |
| **pgsty/silo** (maintained MinIO fork) | yes, the same code | yes | IAM policies, as today | yes | yes | AGPLv3 | small | **Chosen** |
| **SeaweedFS** | yes (fixed for versioned buckets in #8073) | yes | IAM API | **soft**, enforced periodically | active-active or active-passive | Apache 2.0 | small | Next in line |
| **Ceph RGW** | yes, in Ceph's own test suite | yes | real tenants, `tenant$user` | yes | multisite | LGPL | **10 GB or more** | Later, with a second box |
| **Garage** | **no, by design** | **no** | per-key flags, no policies | yes | synchronous only | AGPLv3 | small | Rejected for state |
| **RustFS** | implemented, not documented as atomic | yes | IAM policies | yes | yes | Apache 2.0 | small | Rejected for now: GA 2026-09-16 |
| **Versity S3 Gateway** | yes, with a chosen lock mode | yes | roles and policies | not documented | none native | Apache 2.0 | small | Rejected: no quotas |
| **Zenko CloudServer** | no evidence | — | needs a proprietary IAM | none found | — | Apache 2.0 | Node.js | Rejected |

- **Garage is ruled out by its own documentation:** *"No conditional writes / locking / WORM support
  (`if-none-match`, ...)"*, because a partial implementation couldn't support *"mutual exclusion
  between concurrent writers"*. It also states *"Garage does not (yet) support object versioning"*.
  It would suit tenant buckets, and it can't hold state.
- **pgsty/silo is the least change:**
  - It is not affiliated with MinIO, Inc.
  - It is compatible with MinIO's S3 behavior and on-disk format.
  - It commits to *"a release every one to two months, at most a quarter apart"* and *"a public
    advisory for every fix"*. Its first release closed four CVEs.
  - Its stated scope is *"No new features — just supply chain continuity"*.
  - The API's admin client, the per-tenant policies and the tenants' locking all work unchanged.
  - Its weakness is that it has one maintainer.
- **SeaweedFS is the strongest independent choice.** It is Apache-licensed, a single binary, and has
  an IAM API. Its quotas, though, *"set the bucket to read only"* when a periodic check runs. With
  state and tenant data on one disk (§3), a soft quota means a tenant can overrun its limit before
  the check notices, and fill the disk under everyone's state.
- **Ceph RGW** has the best tenancy model and hard quotas. But `osd_memory_target` *"defaults to 4
  GiB"* and the monitors want *"≥ 5 GB per daemon"*, which is too much for the management hypervisor
  alongside everything else.

---

## Decision

**The store is defined by a contract. pgsty/silo meets it today, on the same host, as an in-place
engine swap.** State and tenant buckets are two classes in one store.

### 1. The contract comes first

Whatever engine runs the store must pass these checks, as tests on the site's own build rather than
readings of a documentation page:

| # | Guarantee |
|---|---|
| 1 | A second `PutObject` with `If-None-Match: *` returns **412, atomically, on a versioned bucket** |
| 2 | A key confined to one tenant's prefix or buckets is **refused** everything else |
| 3 | A bucket quota is **hard**: a write that would exceed it fails; it is never corrected later |
| 4 | **Object versioning** on a bucket |
| 5 | **Asynchronous replication** of a bucket to a second instance (ADR-0014) |
| 6 | **TLS** from the site CA; path-style addressing |
| 7 | An **admin API** the Deevnet API can drive: users, policies, buckets, quotas, replication |
| 8 | It runs **offline** from staged artifacts, under a license that doesn't need to phone home |

- **The API's state-store backend stays behind its existing interface.** Changing engines later
  means a new backend implementation, not a new tenant contract.
- **These checks are the regression test for any engine change**, as the key-change drill is for
  OpenBao.

### 2. The engine: pgsty/silo, built from source

- **It is built from its tagged source by `deevnet-container-image-factory`**, the way VerneMQ is
  (CHG-0015), and staged as an image tarball like every other.
  - The fork's own image is a fallback, not the supply.
  - Building it here is the point: the problem being solved is a supply chain that stopped.
- **It is an in-place swap on `dv02prv001v01`.** The on-disk format is compatible, and the API's
  `madmin-go` client and every tenant's policy carry over. The swap is a change record's work, not
  a migration.
- **The data moves to a data disk first**, as ADR-0014 decided. Nothing more goes into this store
  until it is off the OS disk.

### 3. Two classes in one store

| | State class | Tenant bucket class |
|---|---|---|
| **Holds** | Terraform state | whatever a tenant's application stores |
| **Layout** | the one `tf-state` bucket; one prefix per tenant, as today | buckets named `<tenant>-<name>`, one or more per tenant |
| **Created by** | the API, at tenant creation | the API, on a new `deevnet_bucket` resource |
| **Key** | the tenant's state key, prefix-confined, as today | one key per bucket, confined to that bucket, returned in the create response and restorable from tenant state |
| **Quota** | none per tenant; protected by the reserve below | **required**, hard, declared on the resource |
| **Versioning** | on | the tenant's choice |
| **Replicated to the ADR-0014 replica** | yes, always | only if the tenant sets `replicated = true`, counted against its quota |

**State can't be starved.** The store keeps a fixed reserve for the state class. The API refuses a
bucket whose quota would push the sum of all quotas past the store's capacity minus that reserve.
Quotas are allocated, never overcommitted. With hard quotas (contract 3), no tenant can write past
what it was granted, so no tenant can fill the disk under another tenant's state.

### 4. Whose copy is it?

- **State** is covered by ADR-0014: versioned, and replicated to separate hardware.
- **Tenant bucket contents are tenant data that the substrate only stores.** ADR-0010 §4 says the
  substrate is *"never the only copy"*. For buckets, that stays the tenant's obligation:
  - **The substrate stores; it does not back up** unless the tenant sets `replicated = true`.
  - Even then, the replica is on-site, beside the original.
  - A tenant whose bucket holds data it can't re-derive keeps its own copy elsewhere.
  - This is stated in the resource's documentation, as ADR-0010 requires of any service with a
    cost.

### 5. Transport

- **The store serves TLS from the site CA**, on the endpoint ADR-0016 already promised.
- **Tenants' backends move to `https://`**, which means a re-init for each. Plain HTTP is closed
  when that is done, not before.
- **Tenant applications reach the store over `tenant_transit -> platform`**, which already exists.

---

## Consequences

**The store gets fixes again**, from a maintained fork, built by the site from source.

**Tenants get object storage**, declared in their Terraform, with hard quotas and keys scoped to one
bucket.

**Nothing changes for state.** Tenants keep the same locking, prefixes, keys and bucket. Only the
endpoint's scheme changes.

**Tenant secrets stop crossing the network in the clear**, which closes a gap between ADR-0016's text
and the site.

**The store's single point of failure is unchanged.** It is still one node on one VM. ADR-0014's
replica is what protects state, and it becomes more urgent now that the store also holds tenant data.

**The engine rests on one maintainer.** That is accepted because the contract makes the engine
replaceable, and SeaweedFS is identified as next in line.

**The API grows.** It gains bucket creation, per-bucket keys, quotas with admission against the
reserve, and replication settings.

---

## Open questions

1. **The size of the state reserve**, and the capacity of the data disk it comes out of.
2. **Where the ADR-0014 replica lives.** Still open there, and now also the target for opted-in
   tenant buckets.
3. **Bucket lifecycle rules**, such as expiry and noncurrent-version cleanup. Tenant-declared, or
   a substrate default?
4. **Can a tenant bucket be read publicly** (for example, static assets)? Not in v1. Nothing on the
   site is public today.

## What would reopen this

- **pgsty/silo missing its own cadence**, with no release for more than a quarter. That triggers a
  move to SeaweedFS, and the contract would have to accept soft quotas or add a hard limit in front
  of it.
- **A second on-site box.** Ceph RGW with multisite would then fit, and brings first-class tenants.
- **RustFS proving itself** over a year of releases. It is Apache-licensed and MinIO-shaped.

## To confirm when building

- Contract checks 1 to 8 against the site-built silo image, especially **412 on a versioned bucket**.
- That silo reads the existing MinIO data directory in place, and that both tenants plan with no
  changes afterwards.
- That hard bucket quotas refuse the overflowing write, on this build.
- That bucket replication to a second silo instance works, and what it needs from the network
  between them.

---

## Current state

- **Proposed. Nothing is built.**
- The store is MinIO community `RELEASE.2025-09-07`, serving plain HTTP, on the provisioning VM's OS
  disk.
- It holds two tenants' state.
