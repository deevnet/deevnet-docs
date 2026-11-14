---
title: "CHG-0068: The Object Store Moves to a VM of Its Own, on Silo"
weight: -68
---

# CHG-0068: The Object Store Moves to a VM of Its Own, on Silo

| | |
|---|---|
| **Date** | Started 2026-11-14 |
| **Change type** | Deployment · Migration |
| **Classification** | Structural |
| **Status** | In Progress. Steps 1 to 9 done on 2026-11-14: tenants' state is on silo on `dv02obj001v01`, and MinIO is retired. Open: clean plans for eds and mabell, and the router rule to prv:9000 |
| **Window** | One evening. Tenants can't apply from Step 5 until Step 7's checks pass: about an hour |
| **Site** | mobile |
| **Systems** | `dv02obj001v01` (new), `dv02prv001v01` (MinIO leaves; the API and the backup job stay), `dv02hyp001p01` (the new VM and its data disk), the core router (rules), the tdemo, eds and mabell backends (unchanged, verified) |
| **Automation** | `deevnet-container-image-factory` (the silo image); `deevnet.mgmt` `site.yml` with `proxmox_vm`, `data_disk`, the store role, `site_cert`, `service_proxy`, `backup` and `deevnet_api`; `deevnet.net` for the zone rules and DNS. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium. Most likely to go wrong: silo does not read the copied data directory as MinIO left it, found before any tenant uses the new store, and undone by moving the name back |
| **Related changes** | [CHG-0030](/docs/changes/2026/0030-state-store-tls/) (the store over TLS), [CHG-0039](/docs/changes/2026/0039-backup-to-an-attached-ssd/) (the backup that reads state), [CHG-0046](/docs/changes/2026/0046-service-proxy/) (443 by name), [CHG-0069](/docs/changes/2026/0069-tenant-buckets/) (tenant buckets, which needs this) |
| **Related incidents** | [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/) (bulk transfers across the core router) |
| **Related runbooks** | [State Store](/docs/runbook/tenant/services/state-store/) |

---

## Summary

The state store is MinIO's community edition on `dv02prv001v01`. Its repository was archived on
2026-04-25, so it gets no more fixes (risk R-02). It sits on the provisioning VM's 32 GB OS disk,
beside the Deevnet API and its database.

[ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/) makes the store
object storage for every use, defined by a contract and run by pgsty/silo, a maintained MinIO fork
built here from source. It runs on a VM of its own, `dv02obj001v01`, with a data disk. This change
builds that VM and moves the state onto it. It does that by copying MinIO's data directory, so every
tenant's user, policy, object version and lock arrives intact. The name `tfstate` moves with it, so
no tenant changes anything. Tenant buckets come after, in
[CHG-0069](/docs/changes/2026/0069-tenant-buckets/).

## Goal

- `dv02obj001v01` runs silo, built by `deevnet-container-image-factory`, as two stores: the state
  store on a 5 GB disk of its own, and the bucket store on a 100 GB data disk.
- It answers on 443 as `tfstate` (the state store) and `s3` (the bucket store), through the service
  proxy, and as `tfstate` on 9000 as today.
- ADR-0026's contract checks 1 to 4 and 6 to 9 pass against it.
- Every existing tenant's `terraform plan` shows no changes, and locking still works.
- The API creates, reissues and removes a scratch tenant's state access against it.
- The backup job on `dv02prv001v01` takes the state from it.
- No MinIO runs anywhere on the site.

## Scope

**In scope:**
- The silo image.
- The new VM, its data disk and identity.
- Its DNS names, zone rules and service proxy.
- The copy of the state, and the API's endpoint.
- The backup job's source.
- Retiring MinIO from `dv02prv001v01`.

**Out of scope:**
- Tenant buckets, and the API and provider work for them (CHG-0069).
- The API's database, which stays on `dv02prv001v01`.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A tenant overruns its bucket quota and fills the disk under state | `dv02obj001v01` | Silo enforces a quota about a minute behind (ADR-0026 §1), so state has a store and a disk of its own; an overrun reaches only the bucket store's disk |
| Silo does not read the copied directory, or reads it differently | `dv02obj001v01` | The copy leaves MinIO's directory on prv untouched. Step 4 checks the contract on an empty store first; Step 6 lists every tenant's state before the name moves |
| A tenant applies during the copy and its write is lost | tenants | Tenants are told the window. MinIO is stopped before the copy, so a write either lands before it or fails |
| Not enough room on the hypervisor for 100 GB more | `dv02hyp001p01` | Prerequisite: thin-pool headroom checked |
| The copy crosses the core router | `dv02cor002p01` | Both VMs are on Platform, VLAN 25; the copy stays on the hypervisor's bridge (INC-0005) |
| The image push hangs the core router | `dv02cor002p01` | The 252 MB image goes Builder → Platform, across the router. Trickled at 1 MB/s with a ping watchdog, the operator at the router's console |
| A zone loses the store when the rules move | tenants, the API | Step 7 adds the new rules before the old ones go, and Step 7's checks are from `DVNTM-TD` and from a tenant workload |
| The backup job stops taking state | `dv02prv001v01` | Step 8; `make backup-status` checks it |

## Prerequisites

- [x] Thin-pool headroom on `dv02hyp001p01` for a 32 GB OS disk and a 100 GB data disk
- [x] The control host can reach `dv02hyp001p01` (its host key in `known_hosts`)
- [x] The silo image built, its smoke test passed, and staged
- [x] Tenants told about the window
- [x] A current CHG-0039 backup
- [x] Vault decrypted, collections built

## Procedure

### Step 1: The silo image

Add `images/silo/` to `deevnet-container-image-factory`, built the way `images/vernemq/` is: from
the release's tagged source, with `version`, `build-args` and `smoke-test.sh`. The smoke test starts
the image and runs contract check 1: a second `PutObject` with `If-None-Match: *` returns 412 on a
versioned bucket. Stage the tarball where the store role pushes it from.

### Step 2: The VM in inventory

`mobile/host_vars/dv02obj001v01/vars.yml`, after `dv02obs001v01`'s:
- Platform, 10.20.25.23, VLAN 25.
- A data disk for the bucket store: `{ device: scsi1, size: 100, storage: local-lvm-big-thin, mount: /srv }`.
- A state disk, `extra_disks`: `{ device: scsi2, size: 5, serial: deevnet-state, label: dvnt-state, mount: /srv/state }`.
- The CNAME `s3`. `tfstate` stays on `dv02prv001v01` until Step 7.
- `service_proxy_vhosts`: `s3` to the bucket store, `http://127.0.0.1:9100`. `tfstate` to the
  state store, `http://127.0.0.1:9000` with `legacy_port: 9000`, joins at Step 7.

Add the host to `management_plane` and let the allocator give it its VMID and MAC. Add a zone rule
`tenant_dev -> obj` on 443 and 9000, beside the existing ones to prv. It is not yet in
`tenant_state`.

### Step 3: Build it

`proxmox_vm`, then `data_disk`, `site_cert` and `service_proxy`, with `--limit dv02obj001v01`.
Check the group's members before every play.

### Step 4: Silo, empty, and the contract

Deliver the image to obj: trickled at 1 MB/s with a ping watchdog, the operator at the router's
console, then loaded on obj, so the role pushes nothing. Add `dv02obj001v01` to `tenant_state`
beside prv, and to `tenant_buckets`. Deploy both stores with `--limit dv02obj001v01`. Then run
contract checks 1 to 4 and 6 to 9 against the empty stores, with test buckets and users that are
removed afterwards.

### Step 5: Stop MinIO and copy

The window opens. Stop MinIO on `dv02prv001v01`, then stop silo on `dv02obj001v01` and empty its
data directory. Copy `/srv/minio/data` from prv to the state store's `/srv/state/minio/data` on obj, between the
two VMs.
Start silo.

### Step 6: Read the state back

On obj, before any client is pointed at it:
- Every tenant's prefix lists, with its versions.
- Every tenant user and its policy are there.
- A tenant's own key reads its state, and is refused another's.

### Step 7: Move the name, the rules and the API

- Move `tfstate` from prv's CNAMEs and service proxy to obj's, to the state store.
- Move `tenant_state` to obj alone.
- Point `deevnet_api_minio_endpoint` at `s3.<site>`, and redeploy the API.
- Repoint the zone rules that reach the store at prv, including the `tenant_dev` rules on 9000
  and 443.
- Then run `terraform plan` for tdemo, eds and mabell.

### Step 8: The backup job

The job stays on prv, where its drive is. Give it a read-only key to `tf-state`, made by the store
role, and point it at `https://s3.<site>` instead of `127.0.0.1:9000`. Run `make backup-now`, then
`make backup-verify`.

### Step 9: Retire MinIO on prv

Only after the verification below passes:
- Remove MinIO's container, its service proxy entry and its legacy port from prv.
- Remove `/srv/minio`.
- Remove the zone rules on 9000 to prv.

The window closes.

## Verification

- Contract checks 1 to 4 and 6 to 9 pass on obj.
- `terraform plan` for tdemo, eds and mabell shows no changes, and an apply holds a lock that a
  second apply is refused.
- The API creates a scratch tenant, reissues its state secret (CHG-0060), and removes it, purging
  its prefix (CHG-0065).
- `make backup-status` is clean, and the latest archive holds every tenant's state.
- From `DVNTM-TD`: `https://s3.mobile.deevnet.net` and `https://tfstate.mobile.deevnet.net` verify
  against the site's root.
- Nothing listens on 9000 on prv.

## Undo

### Undo Step 7

Move `tfstate` and `tenant_state` back to prv. Repoint the API and the rules, and start MinIO.
Anything a tenant wrote to obj after Step 7 is lost, so each tenant re-applies once.

### Undo Step 3

Destroy `dv02obj001v01` and remove its inventory and rules.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the silo image built from source, smoke test passed, staged
- [x] Step 2: `dv02obj001v01` in inventory, with its identity and both disks
- [x] Step 3: the VM built, both disks mounted, the proxy answering
- [x] Step 4: the image on obj; both stores up; contract checks 1 to 4 and 6 to 9 pass
- [x] Step 5: the data directory copied, silo started
- [x] Step 6: every tenant's state, user and policy read back
- [x] Step 7: `tfstate`, `tenant_state`, the API and the rules on obj; tdemo plans clean
- [ ] Step 7: eds and mabell plan clean (blocked in their own repositories; see Follow-ups)
- [x] Step 8: the backup job takes state from obj
- [x] Step 9: MinIO retired from prv
- [ ] Step 9: the router's rule `tenant dev -> tfstate` (to prv:9000) deleted
- [x] Risk R-02 closed; R-01 narrowed to the API's database
- [x] The Software Catalog and the Substrate Service VMs map list silo on `dv02obj001v01`

## Outcome

**Tenants' Terraform state is on silo, on a disk of its own on `dv02obj001v01`, under the same
name, and no MinIO runs on the site.** Steps 1 to 9 ran on 2026-11-14. The window, from MinIO
stopping on prv to tdemo's clean plan through the new store, ran from 17:39 to about 17:45 UTC.

- **The image:** silo and mc `RELEASE.2026-11-12T00-00-00Z`, built from source (factory commit
  `8df5e29`), 252 MB. The smoke test passed 26 of 26, including a rehearsal of the move: MinIO
  wrote a versioned bucket, a confined user and its policy, and silo read them all back.
- **The pushes across the core router:** to obj, then to prv for the backup's client. Each took
  about 4 minutes at 1 MB/s, with 246 pings sent and none missed, and checksums matched.
- **Step 4:** both stores passed contract checks 1 to 4, 6 and 9 as deployed. Check 8 holds by
  design: the image is loaded from a local tarball, and silo has no licence check.
- **Steps 5 and 6:** the data directory, 93 files and 1.9 MB, was copied prv to obj directly over
  SSH, and the trees were identical. Read back through silo, it had the same 222 object versions
  (eds 125, mabell 39, tdemo 58), 6 users and versioning. The policies differ only by six that silo
  builds in (`consolereadonly`, `iamAdmin`, `infraAdmin`, `tablesAdmin`, `tablesReadOnly`,
  `tablesReadWrite`), attached to no one.
- **Step 7:**
  - `tfstate` resolves to 10.20.25.23 from management and Platform, and answers on 443 and 9000.
  - tdemo planned with no changes.
  - The API reconciled tdemo through the new store, and tdemo planned clean again after it.
  - eds and mabell read their state through it on the legacy `:9000` address, and mabell's plan
    took its lock there.
  - Their plans then stopped on problems in their own repositories (Follow-ups).
- **Step 8:** the backup job on prv reads `tf-state` from `https://tfstate.mobile.deevnet.net`
  with silo's mc and the store's administrative pair. Its first archive held the 3 current state
  objects and verified.
- **Step 9:** removed MinIO's service, container, env file, data directory and image from prv. The
  tenant removal script's purge now runs on obj.

### Departures from the plan

- **Two stores, not one (Steps 2 and 4).** The image's smoke test found that silo enforces a bucket
  quota from its scanner, about a minute behind: 6.2 MB accepted against a 1 MiB quota over 63
  seconds. ADR-0026's contract check 3 failed as written. The operator chose two silo instances on
  obj, the state store on a 5 GB disk of its own and the bucket store on the 100 GB disk, so an
  overrun can never reach state. ADR-0026 is revised to match. Roles gained `extra_disks` and a
  tenant bucket store play.
- **The state disk needed a SCSI rescan.** It was hot-plugged into the running VM on its LSI
  controller, and the guest saw it only after a rescan of its SCSI hosts. A new VM gets its disks
  before first boot.
- **The Builder's `/home` was full.** The image was built in a container store on `/srv` instead.
- **The backup's client came to prv too (Step 8).** The job had borrowed MinIO's container, image
  and env file on prv. It now names its image, silo's own, which was pushed to prv the same
  throttled way. It writes its own env file and reaches the store by name over TLS, with the
  administrative pair, because a restore writes.
- **The API kept `tfstate` (Step 7).** The plan said to point it at `s3`. With two stores, `s3` is
  the bucket store, so the API's state client stays on `tfstate`, which moved with the state.
- **The scratch tenant was a reconcile (Verification).** The API's admin client was proven against
  the moved store by re-ensuring tdemo, instead of creating, reissuing and removing a scratch
  tenant.
- **MinIO was removed by hand (Step 9).** `podman_service` has no removal path.
- **The router keeps the rule to prv:9000.** It is gone from inventory, but `opnsense_firewall`
  deletes undeclared rules only when `firewall_delete_unmanaged=true`, which is left to the
  operator. Nothing listens there.

## Follow-ups

- **eds:** its configuration requires the `deevnet` provider `~> 0.8`, and its lock file pins
  0.5.0. `terraform init -upgrade`, then a plan.
- **mabell:** Grafana refuses its dashboard password (401). Its stored outputs also still carry
  the `:3000` and `:9000` addresses from before [CHG-0046](/docs/changes/2026/0046-service-proxy/),
  which its next apply updates.
- **The router:** delete `tenant dev -> tfstate` (to prv:9000) with a firewall run that has
  `firewall_delete_unmanaged=true`, after reading its plan.
