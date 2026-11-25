---
title: "CHG-0091: Temporary Builder Rebuilt on Fedora 44"
weight: -91
---

# CHG-0091: Temporary Builder Rebuilt on Fedora 44

| | |
|---|---|
| **Date** | 2026-11-25 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **In progress** |
| **Window** | 2026-11-25 from 06:00, operator near the core router from Step 4 |
| **Site** | mobile |
| **Systems** | `dv02bld001v01` (new, VMID 202 on `dv02hyp001p01`); `dv00bld001p01` (serves the network boot); the core router (DNS record, DHCP reservation) |
| **Automation** | `deevnet.builder` `site.yml` (tags `kickstart`, `grub-mac`, then the whole play on the VM); `deevnet.mgmt` `site.yml --tags vms` (`proxmox_vm`, `source: pxe`); `deevnet.net` `make dns`, `make dhcp` |
| **Risk** | Medium. Most likely to go wrong: the VM's downloads through the core router hang it (INC-0004, INC-0005), guarded by a NIC limit and a ping watchdog |
| **Related changes** | [CHG-0088](/docs/changes/2026/0088-builder-vms-inactive/), which made this VM inactive; the Builder's own repave follows as its own change |
| **Related incidents** | [INC-0004](/docs/incidents/2026/0004-core-router-lost/), [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/) |
| **Related runbooks** | [Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/), [Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/), [Inventory Lifecycle](/docs/runbook/substrate/lifecycle/inventory-lifecycle/) |

---

## Summary

**The temporary builder, `dv02bld001v01`, is built again from nothing, on Fedora 44, by the same
path the Builder takes when it is repaved.** The Builder, `dv00bld001p01`, runs Fedora 43, which
reaches end of life on 2026-12-09, and the Builder is repaved once per Fedora release
([Resiliency](/docs/policies/risk-management/resiliency/#rebuilds-are-exercised-on-a-schedule)).
Both builder VMs are inactive since CHG-0088, so there is no host to repave it from.

This change builds that host, and rehearses the repave on it first. The Builder network-boots the VM
with the builder kickstart (`builder-node-44.ks`), and `deevnet.builder` `site.yml` configures it.
Nothing is copied in from the Builder: the artifact store under `/srv/deevnet-http` is fetched from
upstream by the `artifacts` role, so the run shows that it can be.

Before, the VM was cloned from the service-VM template, with a separate data disk. After, it is
installed over the network, on one disk. The kickstart also grows `/home` from 20G to 60G
([Builder Upkeep](/docs/roadmap/site-work/mobile/builder-upkeep/plan/)): the Builder's own `/home`
is at 19G of 20G. The VM gets the larger volume now, and the Builder gets it at its repave.

| Pull request | What |
|---|---|
| `deevnet.builder` [#51](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/51) | Builder kickstart: `/home` 60G |
| inventory [#125](https://github.com/deevnet/ansible-inventory-deevnet/pull/125) | `dv02bld001v01` active again, `source: pxe`, 4 cores, 6G, one 320G disk; its GRUB entry; its OpenBao CIDR |
| `deevnet.mgmt` [#144](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/144) | `proxmox_vm`: the kickstart's disk floor is about 128 GiB |

## Goal

- `dv02bld001v01` runs Fedora 44, installed from `builder-node-44.ks`, with its packages current.
- `df -h /home` on it shows about 60G; `/srv` holds the rest of its 320G disk.
- `deevnet.builder` `site.yml --limit dv02bld001v01` completes, and a second run changes nothing.
- The **Artifact server** and **PXE infrastructure** checks in
  [Verify Site](/docs/runbook/substrate/building-recovery/build-verification/) pass against it.
- It runs a play: the operator's Ansible from it reaches the Builder.
- The `artifacts` and `pxe` names still point at the Builder: building the VM moves no service.

## Scope

**In scope:**
- the kickstart's `/home`;
- reactivating and building `dv02bld001v01`;
- carrying the operator's working notes to it.

**Out of scope:**
- the Builder's repave, which is its own change;
- moving Podman's storage and `GOPATH` to `/srv`;
- Fedora 45, which the whole site moves to later;
- the patch tools, whose watchers stay on the Builder.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A bulk download through the core router hangs it | Steps 5 and 6: the package update and about 30G of artifacts | The VM's NIC is limited to 5 MB/s from Step 4 until Step 7 (transfers at that rate have passed); operator at the router's console; a ping watchdog on `10.20.25.1` and `1.1.1.1` (`10.20.99.1` never answers ping) |
| The hypervisor runs short of memory or thin pool | `dv02hyp001p01`: 32G, of which the seven service VMs declare 20G | Step 1 reads free memory and `local-lvm-big-thin` before anything is created |
| The install picks up the old kickstart | `/home` stays 20G | Step 2 reads the published kickstart before the VM is created |
| A builder-collection run reaches the Builder | Every builder group holds both hosts again | Every run in this change passes `--limit` |
| The VM reinstalls itself on a reboot | its MAC-pinned GRUB config | `proxmox_vm` sets `boot: order=scsi0;net0`, disk first |

## Prerequisites

- [ ] `deevnet.builder` #51, inventory #125 and `deevnet.mgmt` #144 merged, and pulled on the Builder
- [ ] Operator at the core router's console for Steps 5 and 6

## Procedure

### Step 1: Check the hypervisor's room

On `dv02hyp001p01`: `free -h` and `pvesm status`.

**Verify:** at least 8G of memory free (the VM's 6G and margin), and `local-lvm-big-thin` able to
take a 320G thin volume.

**Undo:** nothing to undo.

### Step 2: Publish the kickstart and the GRUB entry; apply the address

```bash
cd ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit dv00bld001p01 --tags kickstart,grub-mac

cd ansible-collection-deevnet.net
make dns
make dhcp
```

**Verify:**

1. `/srv/deevnet-http/kickstart/builder-node-44.ks` has `lv_home ... --size=61440`.
2. The Builder's TFTP root has `grub.cfg-` files for the VM's MAC.
3. `dig +short dv02bld001v01.mobile.deevnet.net` gives `10.20.99.97`.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: Create and install the VM

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --limit dv02bld001v01 --tags vms
```

`proxmox_vm` creates the empty UEFI VM and starts it. It boots from the network, and anaconda
installs from the Builder on the management segment, so nothing crosses the router. The play waits
up to an hour for SSH.

**Verify:** `ssh a_autoprov@10.20.99.97` answers, and `cat /etc/fedora-release` says 44.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: Limit the VM's NIC

On `dv02hyp001p01`, with the operator at the router's console and the watchdog running:

```bash
qm set 202 --net0 virtio=02:de:20:00:00:ca,bridge=vmbr0,rate=5
```

**Verify:** `qm config 202` shows `rate=5` on `net0`.

**Undo:** the same command without `rate=5`.

### Step 5: Bring its packages up to date

The install tree is the release's original media, from April. On the VM:

```bash
sudo dnf upgrade --refresh -y
sudo reboot
```

**Verify:** `rpm -q kernel` lists a newer kernel than the media's, and it is the one running.

**Undo:** no undo; Step 3's undo rebuilds the VM.

### Step 6: Apply the builder configuration

```bash
cd ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit dv02bld001v01
```

This configures it as a builder, workstation, artifact server and TFTP host, and fetches the artifact
store from upstream: about 30G, so about 100 minutes at the limit.

**Verify:**

1. The play completes; a second run reports no changes.
2. `df -h /home /srv` on it: about 60G and 190G.

**Undo:** no undo; Step 3's undo rebuilds the VM.

### Step 7: Lift the limit

```bash
qm set 202 --net0 virtio=02:de:20:00:00:ca,bridge=vmbr0
```

**Verify:** `qm config 202` shows no `rate` on `net0`.

### Step 8: Set it up for work

On the VM:
- clone the Deevnet repositories into `/srv/dvnt`;
- copy the operator's working notes across from the Builder over SSH, on the management segment.

**Verify:** a `deevnet.builder` play run from the VM reaches the Builder (`--check`, `--limit dv00bld001p01`).

## Verification

Every line of the [Goal](#goal), and Verify Site's **Artifact server** and **PXE infrastructure**
checks against `dv02bld001v01`.

## Undo

Steps are backed out in reverse order. Everything is reversible: the VM is new, and nothing moves
off the Builder.

### Undo Step 3

`qm stop 202` and `qm destroy 202 --purge` on `dv02hyp001p01`.

### Undo Step 2

Revert inventory #125 (the VM back in `inactive`). Then run `make dns`, `make dhcp` and
`grub-mac`.

## To close

**This change closes when every item below is done.**

- [x] Step 1: hypervisor room
- [x] Step 2: kickstart, GRUB entry, address
- [x] Step 3: VM created and installed
- [x] Step 4: NIC limited
- [x] Step 5: packages current
- [ ] Step 6: builder configuration
- [ ] Step 7: limit lifted
- [ ] Step 8: set up for work
- [ ] Verification: Goal and Verify Site
- [ ] [Inventory Lifecycle → Inactive hosts](/docs/runbook/substrate/lifecycle/inventory-lifecycle/#inactive-hosts): the VM's row comes out of the table
- [ ] `make discover` (`deevnet.mgmt`) run after it, and the Software Catalog updated from its report

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| 2026-11-25 06:00 | 1 | `dv02hyp001p01`: 17 GiB of memory available, `local-lvm-big-thin` 1.09 TiB free (5.7% used). The operator's SSH to it by name had failed host-key verification; see below |
| 06:03–06:21 | 2 | DNS record added (`dv02bld001v01` → `10.20.99.97`); DHCP reservation added by the operator; kickstart republished with `/home` 61440 MB; MAC-pinned GRUB entries written |
| 06:22–06:29 | 3 | `proxmox_vm` created VM 202 empty (UEFI, Secure Boot off, 4 cores, 6G, 320G); it network-booted from the Builder and installed in about 6 minutes. Fedora 44, `/` 50G, `/home` 60G, `/srv` 193G |
| 06:32 | 4 | `net0` limited to 5 MB/s (`tc`: 41943 kbit/s). Watchdog started: 1 s pings to `10.20.25.1` through the router, three misses set the VM's link down from the hypervisor |
| 06:32–06:37 | 5 | `dnf upgrade --refresh`: 221 packages upgraded, 18 installed, 587 MiB. Rebooted onto kernel 7.3.4-200.fc44. No router misses |
| 06:38–06:43 | 6 (1st run) | Failed at the Claude Code installer: "this CPU is missing SSE4.2 support". The VM had Proxmox's default CPU model, `kvm64`. Set `cpu: host` by hand and power-cycled it |
| 06:49–07:08 | 6 (2nd run) | Workstation play passed. Failed at the Fedora DVD ISO (3.9G): no space left in `/tmp`, a 2.9G `tmpfs` on a 6G VM |
| 07:54– | 6 (3rd run) | After both fixes merged: running |

### Departures from the plan

- **OpenBao's AppRole CIDR is not applied in this change.** Only the `openbao` and `deevnet_api`
  roles log in to OpenBao, and this change runs neither: the substrate's own work uses
  ansible-vault. Inventory keeps `10.20.99.97/32` in `openbao_ansible_cidrs` for the Builder's
  repave, when the temporary builder may run those plays.
- **Kickstart publishing got its own tag** (`deevnet.builder`
  [#52](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/52)), so Step 2 did not
  have to run the whole artifacts role against the Builder.
- **Network-boot VMs are created with `cpu: host`** (`deevnet.mgmt`
  [#145](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/145)), as template clones
  already are. VM 202 was set by hand and power-cycled, since the role creates a VM only once.
- **The artifacts role stages downloads on disk** (`deevnet.builder`
  [#53](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/53)), in
  `/srv/deevnet-artifacts-stage`, not in `/tmp`. The Builder's larger memory had hidden this.

### Found along the way

- **The operator's `known_hosts` held most hosts by address only**, so SSH by name failed. Names
  were added where each host's key matched the one already held for its address. Ansible checks no
  host keys at all; that is risk R-17, with a waypoint in
  [Security Hardening](/docs/roadmap/infrastructure/substrate/security-hardening/).
- **The network-boot VM runs no QEMU guest agent**, so Proxmox shuts it down by ACPI. To be
  followed up.
