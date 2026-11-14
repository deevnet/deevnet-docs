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
| **Status** | In Progress. Steps 1 to 4 are done: builds read the vault (2026-11-08), OpenBao holds no build credentials, the automation tokens hold no Administrator (2026-11-12), the old build user and role are gone, and the ISO and the empty VM are automated (2026-11-13). The verification remains |
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
[#102](https://github.com/deevnet/ansible-inventory-deevnet/pull/102),
[#103](https://github.com/deevnet/ansible-inventory-deevnet/pull/103)).
`build_secrets.yml` is gone, and the `openbao` role deletes what it once wrote: the `image-factory`
mount, which held the copy of the tokens, its AppRole and its policy. Ansible's policy may delete
those two by name and nothing else of their kind.

| Check | Result |
|---|---|
| The `image-factory` mount is gone | Pass: not in `sys/mounts` |
| The `image-factory` AppRole is gone | Pass: 404 for its role ID; the API's AppRole answers 200 |
| A second `openbao.yml` run changes nothing | Pass: `changed=0` |
| The vault no longer holds the AppRole's credentials | Pass: the operator removed both values (#103) |
| `make pve1-env` and `make pve2-env` still give working tokens | Pass: the same four exports; HTTP 200 from each hypervisor's `/version` |

**The site's own list of retired mounts replaces the role's.** The first run removed the AppRole and
policy but not the mount, because the inventory's `openbao_retired_mounts` named only `pki`. The
inventory now names both (#102).

### Step 3: Narrow the build tokens

A custom Proxmox role per node, declared in `proxmox_node_access`, replaces Administrator for the build
users. Document how to rotate the tokens.

**Verify:** a template build on each node and `make fabric-plan` on the tenant hypervisor succeed.

**State, 2026-11-12:** done
([ansible-collection-deevnet.builder #34](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/34),
[ansible-inventory-deevnet #104](https://github.com/deevnet/ansible-inventory-deevnet/pull/104),
[ansible-collection-deevnet.mgmt #118](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/118)).
`terraform-prov@pve` and its token hold no Administrator on either node.

**The token serves more than builds.** Five things use it on each node: Packer's template build, the
tenant fabric, `proxmox_vm` (the service VMs), `vm_identity`'s survey and `shutdown.yml`. One role,
`DeevnetAutomation` (`group_vars/hypervisors.yml`), covers them, with each privilege tied to the call
that needs it in Proxmox's API schema or code:

| Node | Path | Role |
|---|---|---|
| both | `/` | `DeevnetAutomation`: VM create, configure, clone, power and console; the guest agent's address read; storage space; `SDN.Use`; `Sys.Audit` |
| `dv02hyp001p01` | `/mapping/usb` | `DeevnetUsbMapping`, for prv's USB passthrough |
| `dv02hyp002p02` | `/sdn` | `DeevnetFabric`: `SDN.Allocate`, `SDN.Audit`, `SDN.Use` |
| `dv02hyp002p02` | `/nodes/dv02hyp002p02` | `DeevnetFabricNode`: `Sys.Audit`, `Sys.Modify`, which a fabric node requires |

`proxmox_node_access` grants these first and then removes what `acls_absent` names, so the old
Administrator entries went only after the new ones were in place.

| Check | Result |
|---|---|
| Permissions as Proxmox computes them for each token | Pass: 18 privileges on `/`, VMs and storage; `SDN.Use` on the bridge; SDN only on hyp002's `/sdn`; `Sys.Modify` only on hyp002's own node |
| A second `proxmox-access` run changes nothing | Pass: `changed=0` on both |
| `make fabric-plan` | Pass: all five SDN resources read, no changes |
| `proxmox_vm` against `dv02prv001v01` | Pass after #118: configuration, data disk, USB mapping, start |
| A template build on `dv02hyp001p01` | Pass: `fedora-server-44-1.7`, VMID 102, 12 min 45 s; the core router answered throughout |
| A tenant template build on `dv02hyp002p02` | Pass: `fedora-tenant-44-1.7`, VMID 101, 33 min 19 s; the address read from the guest agent with `VM.GuestAgent.Audit`; the core router answered throughout |

**The guest agent's privilege depends on the Proxmox version.** Packer reads the build VM's address
from the guest agent. Proxmox VE 9 checks `VM.GuestAgent.Audit` for that; 8.4, on `dv02hyp001p01`,
checks `VM.Monitor`, which also allows commands inside a guest. Each node's `proxmox_ve_major` picks
the privilege; [CHG-0066](/docs/changes/2026/0066-hyp001-proxmox-9/) moves that node to 9.

**A narrower path replaces what `/` grants rather than adding to it.** On `dv02hyp002p02`, `/sdn`
holds only `DeevnetFabric`'s three privileges and the node path only its two. Each of those roles
therefore repeats what its subtree still needs (`SDN.Use`, `Sys.Audit`).

**A VM's boot order needs `Sys.Modify` on `/`.** The API schema does not say so; Proxmox's code checks
it for `startup` *"since it changes host behaviour"*. Rather than grant that, `proxmox_vm` sets the
boot order with `qm set`, as root on the node over SSH, and only when it differs (#118).

### Step 4: Remove the leftovers

Remove `packer-prov@pve` and the `TerraformProv` role.

**Verify:** `pveum user list` and `pveum role list` show neither.

**State, 2026-11-13:** done
([ansible-inventory-deevnet #105](https://github.com/deevnet/ansible-inventory-deevnet/pull/105)).
Both are declared absent in the nodes' `proxmox_node_access` and removed by the `proxmox-access` run.
Deleting `packer-prov@pve` took its Administrator entry on `/` with it, so no account on either node
holds Administrator but `root@pam`.

| Check | Result |
|---|---|
| `pveum user list` on `dv02hyp001p01` | Pass: `root@pam` and `terraform-prov@pve` only |
| `pveum role list` on `dv02hyp002p02` | Pass: no `TerraformProv` |
| No ACL entry grants Administrator, on either node | Pass |
| A second `proxmox-access` run changes nothing | Pass: `changed=0` on both |
| Each node's automation token still answers | Pass: `/version` returns 200 on both |

### Step 5: The ISO and the empty VM

Publish the ISO for every built release; make template builds fetch it. Add an empty-shell mode to
`proxmox_vm`, and update *Build a Management-Hypervisor VM*.

**Verify:** a template build on a hypervisor with an empty `local:iso` succeeds; an empty VM is
created from inventory and network-boots.

**State, 2026-11-13:** done

**Ansible stages the ISO; Proxmox does not fetch it.** The template build could have had Proxmox
download the ISO itself (`iso_download_pve`), but Proxmox's `download-url` needs
`Sys.AccessNetwork` on the node, and Step 3 had just narrowed the token. A new `deevnet.builder`
role, `proxmox_node_isos`, stages each release's DVD ISO into `local:iso` as root over SSH, checked
against a `.sha256` file the `artifacts` role now writes beside every Fedora ISO it publishes
([ansible-collection-deevnet.builder #35](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/35),
[ansible-inventory-deevnet #106](https://github.com/deevnet/ansible-inventory-deevnet/pull/106)).
The template build reads `local:iso` only
([deevnet-image-factory #42](https://github.com/deevnet/deevnet-image-factory/pull/42)). The artifact
server now publishes the previous release's DVD ISO as well; Fedora 43's was copied from
`dv02hyp001p01` and checked against Fedora's signed checksum list before publishing.

| Check | Result |
|---|---|
| The artifact server's `.sha256` files match the hashes the image factory had pinned | Pass: 44-1.7 and 43-1.6 |
| `--tags isos` on both nodes | Pass: nothing moved on `dv02hyp001p01`; `dv02hyp002p02` fetched 43-1.6 in under 3 minutes |
| With the 44-1.7 ISO deleted from `dv02hyp002p02`, `--tags isos` stages it again | Pass: downloaded, checksum matched, listed by `pvesm` |
| A tenant template build on `dv02hyp002p02` from the staged ISO | Pass: `fedora-tenant-44-1.7`, VMID 102, 33 min 19 s; the core router answered throughout |

**The empty VM** is `mgmt_vm.source: pxe` in `proxmox_vm`
([ansible-collection-deevnet.mgmt #119](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/119)).
The role creates the VM through the API with everything a UEFI network install needs, and the disk
first in the boot order, so the blank disk falls through to the network and the installed disk boots
from then on. It was proven on a throwaway host, `dv02bld003v01` (VMID 208), declared on a branch
([ansible-inventory-deevnet #107](https://github.com/deevnet/ansible-inventory-deevnet/pull/107),
closed unmerged) and removed afterwards with its reservation, record and GRUB config.
[Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/)
now declares the VM instead of building it by hand.

| Check | Result |
|---|---|
| `site.yml --tags vms` creates the VM as declared | Pass: OVMF, q35, Secure Boot off, `rng0`, `boot: order=scsi0;net0`, the declared MAC |
| The blank disk network-boots | Pass: the reservation, `grubx64.efi`, the MAC-pinned GRUB config, the kickstart; `%post` ran after about 6 minutes |
| After the install, it boots its disk | Pass: no second TFTP request; the play's SSH wait and reserved-address check passed |
| After a power cycle, it boots its disk | Pass: `qm stop` and `qm start`, no network request |
| A second run changes nothing | Pass: `changed=0` |

## Verification

Builds succeed with OpenBao stopped. That is the test of the change.

## Undo

Each step reverses: restore the OpenBao source and AppRole from git, give the build users
Administrator again.

## To discover

- ~~The minimal Proxmox privilege set for Packer's template build and for SDN on the tenant
  hypervisor~~: found in Step 3, from Proxmox's API schema and code, and confirmed by a build on each
  node.

## To close

**What is left before this change closes, from its procedure and verification.**

- [x] Step 1: `pve-creds` reads the vault only, with the same output, and a template builds with it, 2026-11-08
- [x] Step 2: the build path removed from OpenBao, 2026-11-12
- [x] Step 3: the automation tokens narrowed to custom Proxmox roles per node, 2026-11-12
- [x] Step 4: `packer-prov@pve` and the `TerraformProv` role removed, 2026-11-13
- [x] Step 5: the ISO published for every built release, and an empty-shell mode in `proxmox_vm`, 2026-11-13
- [ ] Verification: builds succeed with OpenBao stopped
