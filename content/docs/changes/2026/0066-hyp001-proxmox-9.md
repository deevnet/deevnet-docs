---
title: "CHG-0066: The Management Hypervisor Moves to Proxmox VE 9"
weight: -66
---

# CHG-0066: The Management Hypervisor Moves to Proxmox VE 9

| | |
|---|---|
| **Date** | 2026-11-21 to 2026-11-22 |
| **Change type** | Upgrade |
| **Classification** | Disruptive |
| **Status** | **Complete, 2026-11-22** |
| **Window** | One evening, operator at the node's console and the core router's. Every service VM on the node is down from Step 4 until it boots again after Step 5: about an hour |
| **Site** | mobile |
| **Systems** | `dv02hyp001p01` and every guest on it: `dv02idn001v01`, `dv02prv001v01`, `dv02bld001v01`, `dv02bld002v01`, `dv02nms001v01`, `dv02msg001v01`, `dv02col001v01`, `dv02obs001v01` and `dv02obj001v01` |
| **Automation** | None for the upgrade itself: Proxmox's upgrade is run by hand at the node, as its guide asks. `deevnet.builder` `site.yml --limit hypervisors --tags proxmox-access` after it, against `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium. Most likely to go wrong: the node does not come back on the network after the reboot (a renamed NIC, or the boot loader), found and fixed at its console |
| **Related changes** | [CHG-0037](/docs/changes/2026/0037-builds-off-openbao/), whose narrowed role on this node holds `VM.Monitor` until this change; [CHG-0042](/docs/changes/2026/0042-rehome-stray-vms/), which removed the node's two VMs outside the inventory |
| **Related incidents** | [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/) (bulk transfers across the core router); [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) (bulk disk I/O on the node and prv's disk driver) |
| **Related runbooks** | [Patching](/docs/runbook/substrate/lifecycle/patching/), [Rebuild a Hypervisor](/docs/runbook/substrate/recovery/rebuild-hypervisor/) |

---

## Summary

`dv02hyp001p01` runs Proxmox VE 8.4.21 on Debian 12. Proxmox lists the 8.x series as
**"Proxmox EOL: 2026-08"** and Debian 12 as **"Debian EOL: 2026-07"**, so the node has had no
security updates from either since then. The tenant hypervisor, `dv02hyp002p02`, has run 9.2 since
2026-08-30. This node was the open half of the
[Hypervisor Platform Uplift](/docs/roadmap/site-work/mobile/hypervisor-uplift/plan/), waiting for a
window because every substrate service VM runs on it.

The upgrade is in place, along Proxmox's own path
([Upgrade from 8 to 9](https://pve.proxmox.com/wiki/Upgrade_from_8_to_9)): latest 8.4, the
`pve8to9` checklist clean, the repositories moved from Bookworm to Trixie, `apt dist-upgrade`, and
a reboot. After it, both hypervisors run the same major version, and the automation token's role on
this node trades `VM.Monitor`, which also allows commands inside a guest, for the read-only
`VM.GuestAgent.Audit`.

## Goal

- `pveversion` on `dv02hyp001p01` reports `pve-manager/9.x`, running a 6.14 or later kernel.
- `pve8to9 --full` reports no failures.
- Every guest that was running before the change is running again, in its `startup` order.
- `DeevnetAutomation` on the node holds `VM.GuestAgent.Audit` and not `VM.Monitor`; the inventory
  sets `proxmox_ve_major: 9` for the node.
- A template build on the node and a `proxmox_vm` run against one of its service VMs pass.

## Scope

**In scope:** Proxmox VE and Debian on `dv02hyp001p01`; the two boot-loader findings `pve8to9`
reports; the automation token's role on the node.
**Out of scope:** `dv02hyp002p02`, already on 9.2; the CPU microcode package `pve8to9` suggests,
which needs the `non-free-firmware` component (a follow-up).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The node does not come back on the network: a NIC renamed by the new kernel, or the boot loader | `dv02hyp001p01` | The operator at the node's console. The guide: *"some NICs may change their name, in which case the network configuration needs to be adapted."* The one uplink is `enp0s31f6`, under `vmbr0` |
| The download hangs the core router | `dv02cor002p01` | Packages are fetched in Step 3, before the outage, at 1,000 KB/s (`Acquire::http::Dl-Limit`), with the operator at the router's console and a ping watchdog on `10.20.99.1`. Throttled transfers at that rate have passed with the router answering every ping (2026-11-04, 2026-11-07) |
| A guest does not start, or loses its disk | the service VMs | Every guest on the node is in the inventory and rebuilt from code (ADR-0033); prv's state has CHG-0039's backup. obs's and obj's do not: the `backup` group holds only prv |
| Substrate services are down during the window | tenants on `dv02hyp002p02` | Tenant workloads keep running. Tenant DNS, OpenBao, the Deevnet API, the Omada controller, the MQTT broker and the observability VMs are unavailable until the node is back. Announce the window to tenants |
| The automation token fails on 9 | Packer, `proxmox_vm` | Proxmox: *"Custom roles referencing the `VM.Monitor` privilege will need to be adapted after the upgrade."* Step 6 does that from the inventory, then proves it with a build |
| No undo after Step 4 | the node | Steps 1–3 change nothing that cannot be put back. After `apt dist-upgrade` the way back is forward, at the console, or [Rebuild a Hypervisor](/docs/runbook/substrate/recovery/rebuild-hypervisor/) |

## Prerequisites

- [x] No template build or `proxmox_vm` run in progress on the node
- [x] Operator at the consoles of `dv02hyp001p01` and the core router for Steps 3 to 6
- [x] Tenants told about the window
- [x] A current CHG-0039 backup of prv's state
- [x] Vault decrypted, collections built

## Procedure

### Step 1: Latest 8.4, boot loader fixed

No outage. Run `pve8to9 --full` first and compare with the table: on 2026-11-12 it reported two
failures and four warnings. Record any new finding under Outcome.

| Finding | Action |
|---|---|
| FAIL: *"systemd-boot meta-package installed. This will cause problems on upgrades of other boot-related packages."* | Remove the `systemd-boot` meta-package. The node boots with GRUB in UEFI mode; `proxmox-boot-tool` does not manage it |
| WARN: *"System booted in uefi mode but grub-efi-amd64 meta-package not installed"* | The guide: `[ -d /sys/firmware/efi ] && apt install grub-efi-amd64` |
| WARN: 33 package updates available | `apt update && apt dist-upgrade`, throttled |
| FAIL: a custom role uses `VM.Monitor` | Expected: `DeevnetAutomation`. Adapted in Step 6 |
| WARN: running guests | Expected. Stopped in Step 4 |
| WARN: no `intel-microcode` | Out of scope; a follow-up |

**Run** (as root on the node):

```bash
apt update
apt -o Acquire::http::Dl-Limit=1000 dist-upgrade
apt remove systemd-boot
[ -d /sys/firmware/efi ] && apt install grub-efi-amd64
pve8to9 --full
```

**Verify:** `pveversion` is the latest 8.4; `pve8to9 --full` lists only the `VM.Monitor` failure and
the running-guests and microcode warnings.

**Undo:** [Undo Step 1](#undo-step-1)

### Step 2: Back up the node's configuration

No outage. Every guest is rebuilt from code; the node's own configuration is copied to the Builder.

**Run:**

```bash
tar czf /root/hyp001-etc-$(date +%F).tgz /etc/pve /etc/network/interfaces /etc/apt
```

Then copy the tarball (a few MB) to the Builder.

**Verify:** the tarball is on the Builder.

**Undo:** none needed.

### Step 3: Trixie repositories and the download

No outage. The packages are fetched now, throttled, so that Step 4 moves nothing across the router.

**Run:**

```bash
sed -i 's/bookworm/trixie/g' /etc/apt/sources.list /etc/apt/sources.list.d/pve-enterprise.list
# ceph.list: the node has no Ceph cluster; point it at ceph-squid on trixie, or remove it
apt update
apt -o Acquire::http::Dl-Limit=1000 dist-upgrade --download-only
```

`pve-enterprise.list` holds only a commented line; the node uses `pve-no-subscription`.

**Verify:** `apt update` reports no error; the download finishes and the router answered every
watchdog ping.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: Stop the guests and upgrade

**Disruptive.** From the node's console, not the web UI's: the guide says *"Do not carry out the
upgrade when connected via the virtual console offered by the GUI"*.

**Run:**

```bash
pvesh create /nodes/dv02hyp001p01/stopall
apt dist-upgrade
```

Answers to the prompts, as the guide gives them: `/etc/issue` keep (*"No"*); `/etc/lvm/lvm.conf`
the maintainer's (*"Yes"*); `/etc/default/grub` keep (*"No"*); `/etc/chrony/chrony.conf` the
maintainer's (*"Yes"*). Record any other prompt and the answer under Outcome.

**Verify:** `apt dist-upgrade` ends without error; `pve8to9 --full` lists no failure but the
`VM.Monitor` role.

**Undo:** none. This is the point of no return.

### Step 5: Reboot

**Run:** `reboot`, at the console.

**Verify:**
1. The node boots the new kernel (`uname -r` 6.14 or later) and `pveversion` reports 9.x.
2. `vmbr0` is up on `enp0s31f6` and the node answers at its management address. If the NIC was
   renamed, fix `/etc/network/interfaces` at the console (or pin the name with
   `pve-network-interface-pinning`), then `ifreload -a`.
3. The guests with `onboot` start in `startup` order: `dv02idn001v01` first. OpenBao starts sealed,
   as after any restart.

### Step 6: The automation role on 9

**Run:** set `proxmox_ve_major: 9` in `mobile/host_vars/dv02hyp001p01/vars.yml` by pull request,
then `ansible-playbook playbooks/site.yml --limit dv02hyp001p01 --tags proxmox-access`.

**Verify:** `pveum role list` shows `DeevnetAutomation` with `VM.GuestAgent.Audit` and no
`VM.Monitor`; `pve8to9 --full` reports no failure.

**Undo:** revert the inventory change and run the play again.

### Step 7: Tidy the sources

**Run:** `apt modernize-sources`. The guide: *"The command will also keep the old `.list` files
around by appending `.bak` to them."* Remove the `.bak` files once `apt update` is clean.

## Verification

- `make proxmox-fedora-pve1` builds a template on the node, with the operator at the router's
  console.
- `site.yml --limit dv02prv001v01 --tags vms` passes.
- Every service VM answers on its service, and the API's health check passes.

## Undo

### Undo Step 1

Package updates within 8.4 are not reversed. If GRUB does not boot, boot the previous entry from
the console and reinstall `systemd-boot`.

### Undo Step 3

```bash
sed -i 's/trixie/bookworm/g' /etc/apt/sources.list /etc/apt/sources.list.d/pve-enterprise.list
apt clean && apt update
```

## To close

**This change closes when every item below is done.**

- [x] Step 1: latest 8.4, `systemd-boot` meta-package removed, `grub-efi-amd64` installed
- [x] Step 2: the node's configuration on the Builder
- [x] Step 3: Trixie repositories; packages downloaded, the router up throughout
- [x] Step 4: guests stopped; `apt dist-upgrade` done
- [x] Step 5: rebooted onto 9; the network and the guests back
- [x] Step 6: `DeevnetAutomation` holds `VM.GuestAgent.Audit`, not `VM.Monitor`
- [x] Step 7: sources modernized
- [x] Verification: a template build and a `proxmox_vm` run pass
- [x] The Software Catalog lists Proxmox VE 9 on Debian 13 for the node

## Outcome

**The management hypervisor runs Proxmox VE 9.2.32 on Debian 13, kernel 7.0.14-30, and every
service VM came back on it.** The substrate's services were down from 17:47 to 18:06 on 2026-11-21,
about 19 minutes. Steps 1 to 5 ran that evening and Steps 6 and 7 and the verification the next
morning. Every command ran over SSH as `a_autoprov`, with the operator on site.

| When | Steps | What happened |
|---|---|---|
| 2026-11-21 17:19 | Step 1 | `pve8to9 --full` before: the same two failures and four warnings as on 2026-11-12. 33 Debian 12 updates applied; no Proxmox package among them, so the node stayed on 8.4.21. `systemd-boot` removed, `grub-efi-amd64` installed. After: only the `VM.Monitor` failure and the running-guests and microcode warnings |
| 17:21 | Step 2 | The `/etc` tarball (84 kB) copied to the Builder's `/srv/pve1-vm-backups`, checksum matched |
| 17:21–17:34 | Step 3 | Sources moved to Trixie; `ceph.list` pointed at `ceph-squid` on Trixie. 592 packages to upgrade and 160 new: 891 MB fetched in 11 min 51 s at 1,253 kB/s. The router watchdog missed no ping |
| 17:47 | Step 4 | A fresh CHG-0039 backup of prv (`make backup-now`), then `stopall`: nine guests stopped in 41 s, `dv02idn001v01` last |
| 17:50–17:57 | Step 4 | `apt dist-upgrade` exited 0; `dpkg --audit` clean. The EFI system partition was found unmounted and mounted before GRUB was configured (see below). `/etc/issue` and `/etc/default/grub` kept; the maintainer's `/etc/lvm/lvm.conf` taken; `chrony.conf` did not prompt |
| 18:01–18:06 | Step 5 | Rebooted onto 7.0.14-30-pve; SSH back after 62 s. `enp0s31f6` kept its name; `vmbr0` up. The nine guests started in `startup` order, all by 18:05:53. OpenBao started sealed and was unsealed by the operator later |
| 2026-11-22 | Step 6 | [ansible-inventory-deevnet#121](https://github.com/deevnet/ansible-inventory-deevnet/pull/121) set `proxmox_ve_major: 9`; `proxmox-access` changed one role. `DeevnetAutomation` holds `VM.GuestAgent.Audit` and not `VM.Monitor` |
| 2026-11-22 08:40 | Step 7 | `apt modernize-sources` wrote `debian.sources`, `proxmox.sources` and `ceph.sources`; `apt update` clean once the enterprise repository was disabled (see below); the `.bak` files removed |
| 2026-11-22 | Verification | `site.yml --limit dv02prv001v01 --tags vms`: `failed=0`. The API's `readyz`: database and OpenBao ok. `make proxmox-fedora-pve1`: template `fedora-server-44-1.7` built in 11 min as VMID 100, the router watchdog silent throughout and no disk errors on prv. The older template of the same name (VMID 103) was destroyed |

### Departures from the plan

- **The router watchdog pinged `1.1.1.1` from the node, not `10.20.99.1`.** The core router does not
  answer ICMP on `10.20.99.1`, so that watchdog reported a miss from its first probe while the
  router was forwarding normally. A ping from the node to `1.1.1.1` crosses the router and answered
  throughout the download and the template build.
- **The upgrade ran over SSH as transient systemd units (`systemd-run`), not at the console.** A
  dropped session could not interrupt it. It ran non-interactively, keeping the local copy of every
  changed configuration file; the maintainer's `lvm.conf` was installed afterwards. The only
  difference was the `global_filter` for ZFS and Ceph devices, which the node has neither of.
- **The EFI system partition (`sdb2`) was neither mounted nor in `/etc/fstab`.** GRUB updates had not
  been reaching the partition the firmware boots. It was mounted at `/boot/efi` before
  `grub-efi-amd64` 2.12 was configured, and added to `/etc/fstab` with `nofail`. The removable
  fallback loader (`EFI/BOOT/BOOTX64.efi`) is now kept up to date too, as the guide describes
  (`grub2/force_efi_extra_removable`), which cleared a new `pve8to9` warning.
- **`pve-manager` 9 installs `pve-enterprise.sources` enabled.** Without a subscription it fails
  `apt update` with a 401. It carries `Enabled: no`. `dv02hyp002p02` instead renamed the file to
  `.disabled`.
- **chrony did not start on the old systemd** after its upgrade (*"Could not send notification to
  $NOTIFY_SOCKET"*); it has run since the reboot.
- **`pve8to9 --full` ends with one failure, not none:** *"unable to determine installed
  intel-microcode version"*, new in the 9 checklist. Microcode is out of scope; the follow-up covers
  it.
- **The kernel is 7.0, not 6.14:** the newest that Proxmox VE 9.2 ships.
- **The plan named obs's state as backed up by CHG-0039.** It is not; only prv's is. The Systems
  row also missed `dv02obj001v01`. Both are corrected above.

## Follow-ups

- [ ] Enable `non-free-firmware` and install `intel-microcode`, as `pve8to9` suggests
- [x] Mark the Hypervisor Platform Uplift's management-hypervisor task done
- [ ] Use a watchdog that crosses the core router (a ping to `1.1.1.1` from a host behind it) wherever a procedure names a ping to `10.20.99.1`
