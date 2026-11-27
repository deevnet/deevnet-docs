---
title: "CHG-0098: Every VM Builder Applies the VM Hardware Profile"
weight: -98
---

# CHG-0098: Every VM Builder Applies the VM Hardware Profile

| | |
|---|---|
| **Date** | 2026-11-27 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-27** |
| **Window** | No outage. The API restarts once for its new release (seconds; tenants' workloads do not depend on it). The template builds run beside the old templates |
| **Site** | mobile |
| **Systems** | The template build (`deevnet-image-factory`); `proxmox_vm` and `deevnet_api` (`deevnet.mgmt`); the Deevnet API on `dv02prv001v01`; the templates on `dv02hyp001p01` and `dv02hyp002p02` |
| **Automation** | The changes are code; the release, the deploy and the template builds run from the Builder |
| **Risk** | Low. Most likely to go wrong: a template build fails on the new controller, found by the build itself; the old template stays until the new one is checked |
| **Related changes** | [CHG-0093](/docs/changes/2026/0093-service-vms-virtio-scsi/) and [CHG-0097](/docs/changes/2026/0097-standby-builder-vm-profile/), which moved existing VMs; the tenant workloads follow in their own change |
| **Related incidents** | [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) (the LSI controller's panic) |
| **Related runbooks** | [Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/) |

---

## Summary

**Every existing substrate VM is on the profile, but nothing that makes VMs applies it, so the next
one would arrive on LSI.** `make vm-profile` on 2026-11-27 found the two templates and the five
tenant workloads still on the LSI controller INC-0006 panicked, because:

- **the template build sets no controller**, so Packer's Proxmox plugin uses its default, LSI;
- **`proxmox_vm`'s clones inherit the template's controller**, its network-install VMs are made on
  `virtio-scsi-pci`, and its data disks are attached without IO Thread or Discard;
- **the Deevnet API's workloads inherit the template's controller** too.

**This change makes each of them apply the profile, from inventory, its only source, and rebuilds
the two templates on it.** It is [ADR-0046](/docs/architecture/decisions/substrate/0046-vm-hardware-profile/)'s
second and third "To accept" items. Existing VMs are never changed by a builder: a running VM would
hold a hardware change pending until some later restart, so moving one stays a change record. The
five tenant workloads move in the next.

## Goal

- A new template, a new clone or network-install VM from `proxmox_vm`, and a new workload from the
  API are each on the profile from their first start.
- `make vm-profile` reports both new templates compliant.

## Scope

**In scope:**

| Repository | Pull request | What |
|---|---|---|
| `deevnet-image-factory` | [#51](https://github.com/deevnet/deevnet-image-factory/pull/51) | `scripts/vm-profile-vars` reads the profile from inventory; every template build and `validate` passes it to Packer; the template's variables have no defaults, so a build without inventory fails |
| `deevnet.mgmt` | [#146](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/146) | `proxmox_vm` sets the profile on a new clone before its first start, creates network-install VMs on it, and attaches disks with its options; `deevnet_api` passes it to the API |
| `deevnet-provisioning-api` | [#87](https://github.com/deevnet/deevnet-provisioning-api/pull/87) | A new workload is put on the profile after its clone, before its first start; an adopted one is untouched. Released as 0.29.0 |

and the two templates rebuilt: `fedora-server-44` on `dv02hyp001p01`, `fedora-tenant-44` on
`dv02hyp002p02`.

**Out of scope:** the five tenant workloads (their own change, in a window their tenants agree to);
the daily compliance check with alerting (ADR-0046's fourth item).

## Risk and impact

| Risk | Mitigation |
|---|---|
| A template build fails or its VM does not boot on the new controller | The kickstart and `virtio_scsi` are unchanged (the service VMs boot on it since CHG-0093); the old template stays until the new one is checked |
| The API refuses to start: the two new variables are required | The role sets them first; they are ignored by the running 0.28.1, so the role can go out before the image |
| `proxmox_vm` changes an existing VM | It sets the controller and boot disk only on a VM it has just cloned. The data disks' options are set on every run, and every existing data disk is already on the profile (`make vm-profile`) |

## Prerequisites

- [x] `make vm-profile` before: 15 VMs, 7 compliant, 1 declared exception, 7 drift (the two templates and five tenant workloads)

## Procedure

### Step 1: Merge the code

**Run:** review and merge the three pull requests; `make publish` in `deevnet.mgmt` on the Builder.

**Verify:** each merged; `make check` in `deevnet.mgmt` and `go test ./...` in the API pass.

### Step 2: Release and deploy the API

**Run,** in `deevnet-provisioning-api`: `CHANGELOG.md`'s Unreleased becomes `0.29.0 (<date>)`, tag
`v0.29.0`, `make stage`. A `deevnet.mgmt` pull request moves `deevnet_api_version` to `v0.29.0`
(after the image is staged, so no deploy looks for one that is not there). Then the `deevnet_api`
play, with OpenBao unsealed for the role's KV write.

**Verify:** `make health-watch-now` shows "Deevnet API alive"; the API's log shows it started with
the profile; a tenant's reconcile completes.

### Step 3: Rebuild the templates

**Run** (the operator; the builds read the hypervisors' API tokens from the vault):
`make proxmox-fedora-pve1` and `make proxmox-fedora-tenant` in `deevnet-image-factory`.

**Verify:** each build completes; `make vm-profile` reports both new templates compliant. Then delete
each old template (`qm destroy`) once nothing is a linked clone of it (every clone is full).

### Step 4: The check

**Run:** `make vm-profile`.

**Verify:** the templates compliant; what remains is the five tenant workloads.

## Undo

The code changes are reverted by pull request. A new template that does not work is deleted, and the
old one is used until it is fixed. The API goes back by pinning 0.28.1 again.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the three pull requests merged
- [x] Step 2: the API on 0.29.0, alive, a reconcile completed
- [x] Step 3: both templates rebuilt on the profile, the old ones deleted
- [x] Step 4: `make vm-profile` shows only the tenant workloads drifting

## Outcome

**Every VM builder applies the profile, and both templates are on it.** `make vm-profile` reports
15 VMs: 9 compliant, 1 declared exception, and the five tenant workloads, which move in their own
change. The deploy found two things the Builder's repave (CHG-0092) had not brought back; one is
fixed for good, the other worked around (below).

| When (UTC) | Steps | What happened |
|---|---|---|
| Before Step 1 | 4, before | 15 VMs: 7 compliant, 1 declared exception, 7 drift (the two templates, the five tenant workloads) |
| Before Step 2 | 1 | Merged: [deevnet-image-factory #51](https://github.com/deevnet/deevnet-image-factory/pull/51), [deevnet.mgmt #146](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/146), [deevnet-provisioning-api #87](https://github.com/deevnet/deevnet-provisioning-api/pull/87); `make publish` |
| 17:50, 18:07 | 3 | `make proxmox-fedora-pve1`: `fedora-server-44-1.7` as VMID 101 on `dv02hyp001p01`; `make proxmox-fedora-tenant`: `fedora-tenant-44-1.7` as VMID 100 on `dv02hyp002p02`. Both compliant |
| Before 19:50 | 2 | [deevnet-provisioning-api #88](https://github.com/deevnet/deevnet-provisioning-api/pull/88) (release notes), `v0.29.0` tagged on its merge `0b0c16d`, `make stage`; [deevnet.mgmt #147](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/147) pins it. The first `deevnet_api` play failed at its first OpenBao call, before writing anything: see the departures |
| 19:50 | 2 | The `deevnet_api` play, OpenBao open: `ok=85 changed=7 failed=0`. The API logs `version v0.29.0 commit 0b0c16d`, its image the one staged; its environment carries `DEEVNET_TENANT_SCSIHW=virtio-scsi-single` and `DEEVNET_TENANT_DISK_OPTIONS=iothread=1,discard=on,cache=none` |
| 19:57 | 2 | `make reconcile NAME=tdemo`: `reconciled tdemo` (200, 3.5 s). `tdemo-backend` (2040) still running and still on `lsi`: an adopted workload's hardware is not touched |
| 20:00 | 3 | The old templates destroyed: VMID 100 on `dv02hyp001p01` and 102 on `dv02hyp002p02`, both `lsi`, no linked clone of either. Each had the same name as its replacement, so the API's newest-by-name choice could have taken the old one until then |
| 20:01 | 4 | `make vm-profile`: 15 VMs, 9 compliant, 1 declared exception, 5 drift: 2040, 2080, 2160, 2161, 2162 |

### Departures from the plan

- **`v0.29.0` was first tagged and staged on the wrong commit,** `4a0bad1`, before the release pull
  request had merged (same code, no release-notes heading). The tag was moved to `0b0c16d` and the
  image staged again before anything deployed it.
- **The `deevnet_api` play could not find OpenBao's pin.** It read the Deevnet Root CA from a copy
  the openbao role had left in `.openbao/` on the control node, which the repaved Builder did not
  have. The inventory now pins `site_root_ca_file` directly
  ([ansible-inventory-deevnet #137](https://github.com/deevnet/ansible-inventory-deevnet/pull/137)),
  and the copy is gone ([deevnet.mgmt #148](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/148)):
  a repave needs nothing local for it.
- **`make reconcile` could not SSH to the API host by name.** The repaved Builder knew substrate
  hosts' keys by address only, as Ansible (which does not check them) had recorded them. The API
  host's name was added with the keys already held for its address, which match what it serves.
  Every other host is still known by address only: a follow-up.

## Follow-ups

- **The Builder's knowledge of substrate host keys** survives a repave: by name and by address,
  from a record in git rather than learned again.
