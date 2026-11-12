---
title: "CHG-0037: Substrate Builds Off OpenBao"
weight: -37
---

# CHG-0037: Substrate Builds Off OpenBao

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | In Progress. Steps 1 and 2 are done: builds read the vault (2026-11-08), and OpenBao holds no build credentials (2026-11-12) |
| **Window** | Started 2026-11-08. No service is interrupted; a template build proves it |
| **Site** | mobile |
| **Systems** | The Builder (`deevnet-image-factory`, `deevnet-tenant-fabric`), `dv02idn001v01` (OpenBao), both hypervisors (Proxmox users, roles and tokens) |
| **Automation** | `deevnet-image-factory` (`scripts/pve-creds`, the Makefile), `deevnet.mgmt` `playbooks/openbao.yml`, `deevnet.builder` `site.yml --tags proxmox-access`, the `artifacts` role, the `proxmox_vm` role |
| **Risk** | Low. Most likely to go wrong: a narrowed build token missing one privilege, found by the first template build |
| **Related changes** | [CHG-0026](/docs/changes/2026/0026-build-secrets/), which this reverses in part |
| **Related incidents** | None |
| **Related runbooks** | [Build-Time Secrets](/docs/runbook/substrate/building-recovery/build-secrets/), [Build a Hypervisor](/docs/runbook/substrate/building-recovery/build-hypervisor/) |

---

## Summary

Substrate builds (images, hypervisors, management-plane VMs, the tenant fabric) take their credentials
from ansible-vault only, and never from OpenBao, which exists to serve tenants. Today Packer and the
fabric read the Proxmox token from OpenBao through `pve-creds`, which made OpenBao part of the rebuild
path. This change takes it out, narrows the build tokens from Administrator to what the builds need,
removes two unused Proxmox accounts, and automates two manual steps: the Fedora ISO and the
network-boot VM shell
([2026-10 review: R4, A5, R9](/docs/architecture/reviews/2026-10-rebuild-and-access/#r4-build-credentials-from-openbao)).

## Goal

- `pve-creds` reads ansible-vault only. The image-factory AppRole, its policy and the
  `image-factory/proxmox/*` entries are gone from OpenBao.
- Each hypervisor's build token holds a custom role with only the privileges Packer and the fabric
  need; nothing holds Administrator but `root@pam`.
- `packer-prov@pve` and the `TerraformProv` role are removed.
- The artifact server publishes the Fedora ISO for every release the factory builds, and template
  builds fetch it: a reinstalled hypervisor needs no hand-placed ISO.
- `proxmox_vm` can create an empty VM for network boot.
- *Build-Time Secrets* describes the vault-only path; its rotation section covers the new tokens.

## Scope

**In scope:** the build credential path, the build tokens and their roles, the two leftovers, ISO
publishing, the empty-VM mode.
**Out of scope:** the Deevnet API's own Proxmox account (its role stays at `/`, as ADR-0015 §6 now
records); OpenBao's tenant-facing use.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A narrowed token fails a build | Packer, the fabric | Derive the privilege list from Proxmox's documentation, then prove it with a template build and a fabric plan on each node before removing Administrator |
| A removed account was in use | Proxmox | Check each account's last use and ACLs before removing |
| The ISO doubles the artifact server's disk use | the Builder | Check free space first; publish only releases the factory still builds |

## Prerequisites

- [ ] Vault decrypted; collections built
- [ ] Free space on the artifact server for one more ISO per retained release

## Procedure

### Step 1: `pve-creds` from the vault only

Remove the OpenBao source and its default; keep the output identical.

**Verify:** `make pve1-env` and `make pve2-env` print the same exports as before; a template build runs.

**State, 2026-11-08:** done
([deevnet-image-factory #40](https://github.com/deevnet/deevnet-image-factory/pull/40),
[deevnet-tenant-fabric #19](https://github.com/deevnet/deevnet-tenant-fabric/pull/19)).
`pve-creds` has no OpenBao source and no `PVE_CREDS_SOURCE`.

| Check | Result |
|---|---|
| `make pve1-env` and `make pve2-env` print the same exports as the OpenBao path did | Pass: identical by hash, for both hypervisors |
| Each token answers the Proxmox API | Pass: HTTP 200 from `/nodes/<node>/version` on both |
| A template build runs | Pass, on the third attempt: `fedora-server-44-1.7`, VMID 100 on `dv02hyp002p02`, 33 minutes |

**The first two builds failed in the template recipe, not in the credentials.** Packer typed the GRUB
boot command faster than the console took it: the first lost keys from the kernel's path, the second
lost the `initrd` line and the installer panicked with no root filesystem. Both had already used the
token to create and start the VM. The recipe now types at 200 ms a key and waits out each load
(in [deevnet-image-factory #40](https://github.com/deevnet/deevnet-image-factory/pull/40)). The build's
`dnf upgrade` brought 568 MiB across the core router in 47 seconds, with the operator at its console.

### Step 2: Remove the build path from OpenBao

Remove `build_secrets.yml`'s AppRole, policy and KV entries, and the vault's image-factory AppRole
values.

**Verify:** the AppRole and its paths no longer exist; Step 1's build still runs.

**State, 2026-11-12:** done
([ansible-collection-deevnet.mgmt #117](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/117),
[ansible-inventory-deevnet #101](https://github.com/deevnet/ansible-inventory-deevnet/pull/101),
[#102](https://github.com/deevnet/ansible-inventory-deevnet/pull/102)).
`build_secrets.yml` is gone, and the `openbao` role deletes what it once wrote: the `image-factory`
mount, which held the copy of the tokens, its AppRole and its policy. Ansible's policy may delete
those two by name and nothing else of their kind.

| Check | Result |
|---|---|
| The `image-factory` mount is gone | Pass: not in `sys/mounts` |
| The `image-factory` AppRole is gone | Pass: 404 for its role ID; the API's AppRole answers 200 |
| A second `openbao.yml` run changes nothing | Pass: `changed=0` |
| `make pve1-env` and `make pve2-env` still give working tokens | Pass: the same four exports; HTTP 200 from each hypervisor's `/version` |

**The site's own list of retired mounts replaces the role's.** The first run removed the AppRole and
policy but not the mount, because the inventory's `openbao_retired_mounts` named only `pki`. The
inventory now names both (#102).

### Step 3: Narrow the build tokens

A custom Proxmox role per node, declared in `proxmox_node_access`, replaces Administrator for the build
users. Document how to rotate the tokens.

**Verify:** a template build on each node and `make fabric-plan` on the tenant hypervisor succeed.

### Step 4: Remove the leftovers

Remove `packer-prov@pve` and the `TerraformProv` role.

**Verify:** `pveum user list` and `pveum role list` show neither.

### Step 5: The ISO and the empty VM

Publish the ISO for every built release; make template builds fetch it. Add an empty-shell mode to
`proxmox_vm`, and update *Build a Management-Hypervisor VM*.

**Verify:** a template build on a hypervisor with an empty `local:iso` succeeds; an empty VM is
created from inventory and network-boots.

## Verification

Builds succeed with OpenBao stopped. That is the test of the change.

## Undo

Each step reverses: restore the OpenBao source and AppRole from git, give the build users
Administrator again.

## To discover

- The minimal Proxmox privilege set for Packer's template build and for SDN on the tenant hypervisor,
  from Proxmox's documentation, confirmed by a build.

## To close

**What is left before this change closes, from its procedure and verification.**

- [x] Step 1: `pve-creds` reads the vault only, with the same output, and a template builds with it, 2026-11-08
- [x] Step 2: the build path removed from OpenBao, 2026-11-12
- [ ] Step 3: the build tokens narrowed to a custom Proxmox role per node
- [ ] Step 4: `packer-prov@pve` and the `TerraformProv` role removed
- [ ] Step 5: the ISO published for every built release, and an empty-shell mode in `proxmox_vm`
- [ ] Verification: builds succeed with OpenBao stopped
