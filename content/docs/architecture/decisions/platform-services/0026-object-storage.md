---
title: "ADR-0026: Object Storage"
weight: -26
aliases:
  - /docs/architecture/decisions/0026-object-storage/
---

# ADR-0026: The State Store Becomes Object Storage on a VM of Its Own, Defined by a Contract, With State and Tenant Buckets as Two Classes

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-21; revised 2026-11-14 (a dedicated VM; the bucket resource's full shape; open questions 1, 3 and 4 answered) |
| **Scope** | What the substrate's S3 service must guarantee, which engine provides it, where it runs, and how it serves both Terraform state and tenants' own buckets. Covers isolation, quotas, locking, versioning, lifecycle, anonymous read and transport. |
| **Extends** | [ADR-0007: Terraform State Custody](/docs/architecture/decisions/tenant-model/0007-terraform-state-custody/), which offered a state store and chose MinIO as a detail |
| **Amended by** | [ADR-0033: Code Is the State](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/) *(Proposed)*: no replica. State is re-derivable, and tenant buckets are the tenant's to copy; the `replicated` option is withdrawn (§3, §4). [ADR-0036: A Service Proxy on Each Service VM](/docs/architecture/decisions/platform-services/0036-service-proxy/): the store serves plain HTTP on loopback, and the service proxy holds the certificate (§5) |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/tenant-model/0010-tenants-consume-platform-services/) §4, [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/) §6, [ADR-0014: Tenant State Durability](/docs/architecture/decisions/tenant-model/0014-tenant-state-durability/) (superseded; its data disk carries over), [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/), [ADR-0016: Substrate Secrets in OpenBao](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) |

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

### The store shares a VM, and a disk, with provisioning

- **MinIO runs on the provisioning VM**, beside the Deevnet API and its database, all on the VM's
  32 GB OS disk.
- **That was right for a store that held only state**, which is kilobytes per tenant and belongs to
  the provisioning story (ADR-0007).
- **It is wrong for object storage.** Tenant buckets hold application data, sized by quota in
  gigabytes. Growing them on the provisioning VM's disk would put the API's database and every
  tenant's data in the same failure and capacity domain, for a service that has nothing to do with
  provisioning.

### What is wanted: storage in the spirit of cloud

Terraform state is one use of object storage. A tenant's application wants the same thing a cloud
tenant gets:
- buckets of its own
- keys that reach only those buckets, read-write or read-only
- a quota
- versioning and lifecycle rules where it wants them
- a way to serve some objects without a key, for example static assets to its own devices

Treating the store as **object storage**, with state as one of its uses, gives tenants that.

### What Terraform's locking actually requires

- Terraform's documentation says only that `use_lockfile` is *"Whether to use a lockfile for locking
  the state file"*, and that support for S3-compatible stores is *"'best effort'"*.
- The change that introduced it states the mechanism: *"If an object with the same key name already
  exists, the write operation fails with a 412 Precondition Failed response."*
- **So a store is usable for state only if a second `PutObject` with `If-None-Match: *` fails
  atomically with 412, including on a versioned bucket.**

---

## Options considered

### Engines

Vendor documentation and repositories were checked on 2026-09-21. pgsty/silo's release cadence was
checked again on 2026-11-14.

| | Conditional writes (`use_lockfile`) | Versioning | Tenant isolation | Hard quotas | License | Weight | Verdict |
|---|---|---|---|---|---|---|---|
| **MinIO community, as is** | yes | yes | IAM policies | yes | AGPLv3 | small | Rejected: archived, no fixes |
| **pgsty/silo** (maintained MinIO fork) | yes, the same code | yes | IAM policies, as today | yes | AGPLv3 | small | **Chosen** |
| **SeaweedFS** | yes (fixed for versioned buckets in #8073) | yes | IAM API | **soft**, enforced periodically | Apache 2.0 | small | Next in line |
| **Ceph RGW** | yes, in Ceph's own test suite | yes | real tenants, `tenant$user` | yes | LGPL | **10 GB or more** | Later, with a second box |
| **Garage** | **no, by design** | **no** | per-key flags, no policies | yes | AGPLv3 | small | Rejected for state |
| **RustFS** | implemented, not documented as atomic | yes | IAM policies | yes | Apache 2.0 | small | Rejected for now: GA 2026-09-16 |
| **Versity S3 Gateway** | yes, with a chosen lock mode | yes | roles and policies | not documented | Apache 2.0 | small | Rejected: no quotas |
| **Zenko CloudServer** | no evidence | — | needs a proprietary IAM | none found | Apache 2.0 | Node.js | Rejected |

- **Garage is ruled out by its own documentation:** *"No conditional writes / locking / WORM support
  (`if-none-match`, ...)"*, because a partial implementation couldn't support *"mutual exclusion
  between concurrent writers"*. It also states *"Garage does not (yet) support object versioning"*.
  It would suit tenant buckets, and it can't hold state.
- **pgsty/silo is the least change:**
  - It is not affiliated with MinIO, Inc.
  - It is compatible with MinIO's S3 behavior and on-disk format.
  - It commits to *"a release every one to two months, at most a quarter apart"* and *"a public
    advisory for every fix"*. Its first release closed four CVEs. It was renamed from pgsty/minio on
    2026-08-06 and has kept that cadence since, with releases on 2026-10-15, 10-18, 10-26, 11-09
    and 11-12.
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

### Where it runs

| | Verdict |
|---|---|
| **In place on the provisioning VM**, with a data disk added | Rejected: the store would keep sharing a VM with the API and its database, though it serves every tenant's application, not provisioning |
| **A second instance for tenant buckets**, beside the state store | Rejected: two stores to run, two admin credentials in the API, and still on the provisioning VM |
| **A VM of its own, holding every bucket whatever its use** | **Chosen** |

---

## Decision

**The store is defined by a contract. pgsty/silo meets it today, on a VM of its own,
`dv02obj001v01`, which holds every bucket on the site, state included.** State and tenant buckets
are two classes in one store.

### 1. The contract comes first

Whatever engine runs the store must pass these checks, as tests on the site's own build rather than
readings of a documentation page:

| # | Guarantee |
|---|---|
| 1 | A second `PutObject` with `If-None-Match: *` returns **412, atomically, on a versioned bucket** |
| 2 | A key confined to one tenant's prefix or buckets is **refused** everything else, and a read-only key is refused every write |
| 3 | A bucket quota is **hard**: a write that would exceed it fails; it is never corrected later |
| 4 | **Object versioning** on a bucket, switchable by its owner |
| 5 | **Lifecycle rules** on a bucket: expiry of current objects and of noncurrent versions |
| 6 | Served behind the site's TLS, **path-style** addressing |
| 7 | An **admin API** the Deevnet API can drive: users, policies, buckets, quotas, versioning, lifecycle, bucket policies |
| 8 | It runs **offline** from staged artifacts, under a license that doesn't need to phone home |
| 9 | A bucket policy can allow **anonymous `GetObject`** on one bucket, and nothing else anonymously |

- **The API's store backend stays behind its existing interface.** Changing engines later
  means a new backend implementation, not a new tenant contract.
- **These checks are the regression test for any engine change**, as the key-change drill is for
  OpenBao.

### 2. The engine and the host

- **pgsty/silo is built from its tagged source by `deevnet-container-image-factory`**, the way
  VerneMQ is (CHG-0015), and staged as an image tarball like every other.
  - The fork's own image is a fallback, not the supply.
  - Building it here is the point: the problem being solved is a supply chain that stopped.
- **It runs on `dv02obj001v01`, the object storage VM**, on Platform, where every zone that has
  something to store already reaches.
  - **The data lives on a 100 GB data disk**, never the OS disk. It can grow later.
  - The provisioning VM keeps the Deevnet API and its database, and nothing else.
- **The state moves by copying MinIO's data directory.** The on-disk format is compatible, so every
  tenant's user, policy, object version and lock arrives as it was. The API's `madmin-go` client
  carries over unchanged.

### 3. Two classes in one store

| | State class | Tenant bucket class |
|---|---|---|
| **Holds** | Terraform state | whatever a tenant's application stores |
| **Layout** | the one `tf-state` bucket; one prefix per tenant, as today | buckets named `<tenant>-<name>`, one or more per tenant |
| **Created by** | the API, at tenant creation | the API, on a `deevnet_bucket` resource |
| **Keys** | the tenant's state key, prefix-confined, as today | one read-write key returned when the bucket is created; more, read-write or read-only, on `deevnet_bucket_key` resources. Each key reaches one bucket. Secrets are returned in create responses only |
| **Quota** | none per tenant; protected by the reserve below | **required**, hard, declared on the resource |
| **Versioning** | on | the tenant's choice, off by default |
| **Lifecycle** | none | the tenant's choice: days until current objects expire, days until noncurrent versions expire |
| **Anonymous read** | never | the tenant's choice, `public_read`, off by default. See §5 for who can reach it |

**State can't be starved.** The store keeps a **5 GB reserve** for the state class. The API refuses a
bucket whose quota would push the sum of all quotas past the store's capacity minus that reserve:
95 GB on the first disk. Quotas are allocated, never overcommitted. With hard quotas (contract 3),
no tenant can write past what it was granted, so no tenant can fill the disk under another tenant's
state.

**Lifecycle is the tenant's, not a substrate default.** A substrate default would delete a tenant's
data on a schedule the tenant never chose. A tenant that wants old versions cleaned up declares it,
and the quota counts every version until then.

### 4. Whose copy is it?

- **State** is re-derivable from the tenant's repository (ADR-0033). The store keeps it versioned.
- **Tenant bucket contents are tenant data that the substrate only stores.** ADR-0010 §4 says the
  substrate is *"never the only copy"*. For buckets, that stays the tenant's obligation:
  - **The substrate stores; it does not back up.**
  - A tenant whose bucket holds data it can't re-derive keeps its own copy elsewhere.
  - This is stated in the resource's documentation, as ADR-0010 requires of any service with a
    cost.

### 5. Transport and reach

- **The store's name is `s3`.** It is served on 443 by the service proxy (ADR-0036), and `tfstate`
  stays an alias for the same store, so every tenant's backend keeps working unchanged.
- **Tenant applications reach it over `tenant_transit -> platform`**, which already exists, and
  tenants' laptops reach it from the tenant developer network.
- **Anonymous read is for the site only.** A `public_read` bucket answers a `GetObject` without a key
  to anything that can reach the store, and nothing outside the site can. The store is never
  published to the internet. Whether a zone reaches the store at all is the core router's policy, as
  for every other service.

---

## Consequences

**The store gets fixes again**, from a maintained fork, built by the site from source.

**Tenants get object storage**, declared in their Terraform, with hard quotas, keys scoped to one
bucket, versioning, lifecycle and site-only anonymous read.

**Nothing changes for state.** Tenants keep the same locking, prefixes, keys, bucket and name.

**Provisioning and storage fail separately.** A full store no longer shares a disk with the API's
database, and the provisioning VM is smaller and simpler.

**The site gains a service VM.** It is one more host to build, patch and back up, on the management
hypervisor.

**The store's single point of failure is unchanged.** It is still one node on one VM, and the
substrate does not back up tenant buckets. That is stated to tenants, and ADR-0033 accepts it for
state.

**The engine rests on one maintainer.** That is accepted because the contract makes the engine
replaceable, and SeaweedFS is identified as next in line.

**The API grows.** It gains buckets, bucket keys, quotas with admission against the reserve,
versioning, lifecycle and bucket policies.

---

## To accept

**This record is accepted when every item below is done.**

- [x] An acceptance test: contract checks 1 to 9 pass on the site-built silo on `dv02obj001v01`, every tenant plans with no changes after the state move, and the reference tenant runs a bucket through its whole life (CHG-0069's verification).
- [x] Built by change records: [CHG-0068](/docs/changes/2026/0068-object-store-vm/) (the store and the state move) and [CHG-0069](/docs/changes/2026/0069-tenant-buckets/) (tenant buckets).
- [x] Open question 1 answered: a 5 GB reserve on a 100 GB disk (§3).
- [x] Open question 2 answered: where the replica lives, by [ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/) (no replica).
- [x] Open question 3 answered: lifecycle rules are tenant-declared (§3).
- [x] Open question 4 answered: a tenant bucket can be read without a key, from the site only (§5).
- [ ] CHG-0068 complete.
- [ ] CHG-0069 complete.

## Open questions

1. **The size of the state reserve**, and the capacity of the data disk it comes out of.
   *Answered: 5 GB of a 100 GB disk (§3).*
2. **Where the ADR-0014 replica lives.**
   *Answered by [ADR-0033: Code Is the State](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/): there is no replica.*
3. **Bucket lifecycle rules**, such as expiry and noncurrent-version cleanup. Tenant-declared, or
   a substrate default?
   *Answered: tenant-declared, with no substrate default (§3).*
4. **Can a tenant bucket be read publicly** (for example, static assets)?
   *Answered: yes, per bucket, from the site only; never from the internet (§5).*

## What would reopen this

- **pgsty/silo missing its own cadence**, with no release for more than a quarter. That triggers a
  move to SeaweedFS, and the contract would have to accept soft quotas or add a hard limit in front
  of it.
- **A second on-site box.** Ceph RGW with multisite would then fit, and brings first-class tenants.
- **RustFS proving itself** over a year of releases. It is Apache-licensed and MinIO-shaped.
- **A tenant needing objects served to the internet.** That is a new exposure for the site, not a
  bucket setting.

## To confirm when building

- Contract checks 1 to 9 against the site-built silo image, especially **412 on a versioned bucket**.
- That silo reads the copied MinIO data directory in place, and that every tenant plans with no
  changes afterwards.
- That hard bucket quotas refuse the overflowing write, on this build.
- That a quota counts noncurrent versions, so versioning can't be used to write past it.
- That an anonymous `GetObject` policy on one bucket grants nothing on any other bucket, and no
  listing.

---

## Current state

*Updated 2026-11-14.* **Proposed. Nothing this record decides is built.**

- The store is MinIO community `RELEASE.2025-09-07` on the provisioning VM's OS disk. It serves
  TLS from the site CA ([CHG-0030](/docs/changes/2026/0030-state-store-tls/)), and on 443 through
  the service proxy ([CHG-0046](/docs/changes/2026/0046-service-proxy/)).
- It holds every tenant's Terraform state, and nothing else.
- The state is backed up to a drive on the provisioning VM ([CHG-0039](/docs/changes/2026/0039-backup-to-an-attached-ssd/)).
