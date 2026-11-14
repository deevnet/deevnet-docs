---
title: "CHG-0068: The Object Store Moves to a VM of Its Own, on Silo"
weight: -68
---

# CHG-0068: The Object Store Moves to a VM of Its Own, on Silo

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Migration |
| **Classification** | Structural |
| **Status** | Planned |
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

- `dv02obj001v01` runs silo, built by `deevnet-container-image-factory`, with its data on a 100 GB
  data disk.
- It answers on 443 by the names `s3` and `tfstate`, through the service proxy, and on 9000 as
  today.
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
| Silo does not read the copied directory, or reads it differently | `dv02obj001v01` | The copy leaves MinIO's directory on prv untouched. Step 4 checks the contract on an empty store first; Step 6 lists every tenant's state before the name moves |
| A tenant applies during the copy and its write is lost | tenants | Tenants are told the window. MinIO is stopped before the copy, so a write either lands before it or fails |
| Not enough room on the hypervisor for 100 GB more | `dv02hyp001p01` | Prerequisite: thin-pool headroom checked |
| The copy crosses the core router | `dv02cor002p01` | Both VMs are on Platform, VLAN 25; the copy stays on the hypervisor's bridge. Nothing is pulled across the router (INC-0005) |
| A zone loses the store when the rules move | tenants, the API | Step 7 adds the new rules before the old ones go, and Step 7's checks are from `DVNTM-TD` and from a tenant workload |
| The backup job stops taking state | `dv02prv001v01` | Step 8; `make backup-status` checks it |

## Prerequisites

- [ ] Thin-pool headroom on `dv02hyp001p01` for a 32 GB OS disk and a 100 GB data disk
- [ ] The control host can reach `dv02hyp001p01` (its host key in `known_hosts`)
- [ ] The silo image built, its smoke test passed, and staged
- [ ] Tenants told about the window
- [ ] A current CHG-0039 backup
- [ ] Vault decrypted, collections built

## Procedure

### Step 1: The silo image

Add `images/silo/` to `deevnet-container-image-factory`, built the way `images/vernemq/` is: from
the release's tagged source, with `version`, `build-args` and `smoke-test.sh`. The smoke test starts
the image and runs contract check 1: a second `PutObject` with `If-None-Match: *` returns 412 on a
versioned bucket. Stage the tarball where the store role pushes it from.

### Step 2: The VM in inventory

`mobile/host_vars/dv02obj001v01/vars.yml`, after `dv02obs001v01`'s:
- Platform, 10.20.25.23, VLAN 25.
- A data disk: `{ device: scsi1, size: 100, storage: local-lvm-big-thin, mount: /srv }`.
- The CNAME `s3`. `tfstate` stays on `dv02prv001v01` until Step 7.
- `service_proxy_vhosts` for `s3` and `tfstate`, each to `http://127.0.0.1:9000`, with
  `legacy_port: 9000`.

Add the host to `management_plane` and let the allocator give it its VMID and MAC. Add a zone rule
`tenant_dev -> obj` on 443 and 9000, beside the existing ones to prv. It is not yet in
`tenant_state`.

### Step 3: Build it

`proxmox_vm`, then `data_disk`, `site_cert` and `service_proxy`, with `--limit dv02obj001v01`.
Check the group's members before every play.

### Step 4: Silo, empty, and the contract

Point the store role at the silo image, and add `dv02obj001v01` to `tenant_state` beside prv, for
this play only. Deploy with `--limit dv02obj001v01`. Then run contract checks 1 to 4 and 6 to 9
against the empty store, with test buckets and users that are removed afterwards.

### Step 5: Stop MinIO and copy

The window opens. Stop MinIO on `dv02prv001v01`, then stop silo on `dv02obj001v01` and empty its
data directory. Copy `/srv/minio/data` from prv to obj with `rsync -aHAX`, between the two VMs.
Start silo.

### Step 6: Read the state back

On obj, before any client is pointed at it:
- Every tenant's prefix lists, with its versions.
- Every tenant user and its policy are there.
- A tenant's own key reads its state, and is refused another's.

### Step 7: Move the name, the rules and the API

- Move `tfstate` from prv's CNAMEs and service proxy to obj's.
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

- [ ] Step 1: the silo image built from source, smoke test passed, staged
- [ ] Step 2: `dv02obj001v01` in inventory, with its identity and data disk
- [ ] Step 3: the VM built, the data disk mounted, the proxy answering
- [ ] Step 4: contract checks 1 to 4 and 6 to 9 pass on the empty store
- [ ] Step 5: the data directory copied, silo started
- [ ] Step 6: every tenant's state, user and policy read back
- [ ] Step 7: `tfstate`, `tenant_state`, the API and the rules on obj; every tenant plans clean
- [ ] Step 8: the backup job takes state from obj
- [ ] Step 9: MinIO retired from prv
- [ ] Risk R-02 closed; R-01 narrowed to the API's database
- [ ] The Software Catalog and the Substrate Service VMs map list silo on `dv02obj001v01`

## Outcome

*To be written.*

### Departures from the plan

## Follow-ups
