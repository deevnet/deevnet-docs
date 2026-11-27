---
title: "CHG-0095: Both Hypervisors Updated to Proxmox VE 9.3"
weight: -95
---

# CHG-0095: Both Hypervisors Updated to Proxmox VE 9.3

| | |
|---|---|
| **Date** | 2026-11-27 |
| **Change type** | Upgrade |
| **Classification** | Routine |
| **Status** | **In progress**: started 2026-11-27 |
| **Window** | One work session from the Builder, one hypervisor at a time, the management hypervisor first. No reboot and no guest restart: the Proxmox daemons restart and the web interface blips, while every VM keeps running |
| **Site** | mobile |
| **Systems** | `dv02hyp001p01` (the management hypervisor); `dv02hyp002p02` (the tenant hypervisor) and the tenant fabric it carries: the `tfab` fabric and the `cdeever`, `eds`, `mabell` and `tdemo` zones |
| **Automation** | None for the updates: `apt` on each node, by hand, as in CHG-0080. Checked by the update watcher (`deevnet.builder`) and `make discover` (`deevnet.mgmt`) |
| **Risk** | Low. Most likely to go wrong: the SDN package update changes the tenant fabric on `dv02hyp002p02`, found by comparing it with its saved state |
| **Related changes** | [CHG-0080](/docs/changes/2026/0080-hyp002-proxmox-9-2-32/), whose method this follows; [CHG-0066](/docs/changes/2026/0066-hyp001-proxmox-9/); [CHG-0094](/docs/changes/2026/0094-patch-builder-service-vms/), which patched the VMs both nodes carry |
| **Related incidents** | [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/) (bulk transfers across the core router) |
| **Related runbooks** | [Patching](/docs/runbook/substrate/lifecycle/patching/) |

---

## Summary

**The update watcher lists 33 updates on each hypervisor, 6 of them Debian security updates.** They
are Proxmox VE's 9.2 → 9.3 point release (`proxmox-ve` 9.3.0, `pve-manager` 9.3.1, `qemu-server`,
`pve-cluster`, the firewall packages and `libpve-network`, the SDN code) and Debian's security
updates to `shadow` (`passwd`, `login.defs`, `libsubid5`, `uidmap`) and `zstd`. `proxmox-ve` 9.3.0
also installs `multipath-tools`, `kpartx`, `nvme-cli` and `sg3-utils` (and `uuid-runtime` on
`dv02hyp001p01`).

**Neither a kernel nor QEMU is among them, so neither node reboots and no guest restarts.** The
Proxmox firewall is disabled on both nodes, so its packages' update changes no traffic.

## Goal

- Both nodes run Proxmox VE 9.3.1, with nothing waiting in `apt`.
- Every VM on both nodes keeps running throughout.
- The tenant fabric on `dv02hyp002p02` is exactly as it was: zones, vnets, the `tfab` fabric, `frr`,
  the VRFs, and tenant egress.

## Scope

**In scope:** the 33 upgrades and the new packages `apt dist-upgrade` brings, on `dv02hyp001p01` and
`dv02hyp002p02`.

**Out of scope:**

- Restarting VMs. Each VM's QEMU process keeps the old `libzstd` loaded until the VM is next stopped
  and started (a reboot inside the guest is not enough). QEMU uses zstd for compressing migrations
  and snapshots, and this site migrates nothing; the fix is accepted at each VM's next stop and start.
- Old kernels kept on both nodes (6.5, 6.8), and `lvm.conf.dpkg-dist` on `dv02hyp002p02`
  (CHG-0080's follow-up).
- OPNsense 26.7.10 on the core router: its own change.

## Risk and impact

| Risk | Where | Mitigation |
|---|---|---|
| The download hangs the core router | `dv02cor002p01` | `Acquire::http::Dl-Limit=1000` (1,000 KB/s, which held in CHG-0080) and a watchdog: the node pinging `1.1.1.1` throughout |
| The SDN update changes the tenant fabric | `dv02hyp002p02` | Zones, vnets and `frr`'s state saved first and compared after. `pve-network` does not regenerate the fabric until an SDN apply, which this change does not run |
| `multipath-tools` claims a local disk | both | With no configuration it claims none. Checked after: `multipath -ll` empty, every logical volume and thin pool as before |
| A guest stops | both | The Proxmox daemons restart; QEMU does not. Checked after: every VM still running, with the same process ID |
| A configuration prompt stops `apt` | both | `--force-confdef --force-confold`, and any `.dpkg-dist` left is listed after |

## Prerequisites

- [x] CHG-0094's VMs patched and checked, so a problem after this change is not one of theirs
- [x] `/boot/efi` and `/` have room on both nodes (1% and 54% / 40% used)

## Procedure

Every step runs from the Builder as `a_autoprov` over SSH, with `sudo`. `<node>` is
`dv02hyp001p01`, then `dv02hyp002p02`.

### Step 1: Record where each node starts

**Run,** on the node:

```bash
pveversion -v > /root/chg-0095-pveversion-before.txt
tar czf /root/chg-0095-etc.tgz /etc/pve /etc/network /etc/frr /etc/apt /etc/lvm
qm list; lvs; multipath -ll   # multipath not installed yet
```

On `dv02hyp002p02` also: `pvesh get /cluster/sdn/zones`, `pvesh get /cluster/sdn/vnets`,
`vtysh -c 'show running-config'`, and `ip -br link show type vrf`, each saved under `/root/chg-0095-*`.

**Verify:** every VM running; each file saved and copied to the Builder.

### Step 2: Download

**Run,** on the node, with `ping -i 2 1.1.1.1` running in the background:

```bash
apt-get update
apt-get -o Acquire::http::Dl-Limit=1000 -y dist-upgrade --download-only
```

**Verify:** the download completes; the watchdog missed no ping.

### Step 3: Install

**Run,** on the node:

```bash
DEBIAN_FRONTEND=noninteractive apt-get -y -o Dpkg::Options::=--force-confdef \
  -o Dpkg::Options::=--force-confold dist-upgrade
```

**Verify:** exit 0; `dpkg --audit` empty; `pveversion` 9.3.1; `apt list --upgradable` empty; no failed unit;
every VM still running with its process ID unchanged; `multipath -ll` empty and `lvs` as before;
any new `.dpkg-dist` or `.dpkg-new` file listed. On `dv02hyp002p02` also: zones, vnets, `frr`'s
running configuration and the VRFs identical to Step 1; the egress agent's next run succeeds; the
`tdemo` VRF reaches `1.1.1.1`.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: The watcher and the catalog

**Run:** `make update-watch-now` and `make update-watch-ack` (in `deevnet.builder`); `make discover`
(in `deevnet.mgmt`, the operator); update the Software Catalog's hypervisor rows.

**Verify:** the watcher shows nothing waiting on either node; `make discover` shows no mismatch.

## Verification

The goal's three points: both nodes on 9.3.1 with nothing waiting; every VM running throughout;
the fabric as it was.

## Undo

### Undo Step 3

**Proxmox does not support downgrading a point release.** A package that breaks something is fixed
forward, from Proxmox's repository, or by installing its previous version from the apt cache
(`/var/cache/apt/archives` holds only the new ones; the previous `.deb` is fetched from the
repository by version). A fabric that changed is put back from the saved configuration in
`/root/chg-0095-etc.tgz` and an SDN apply. `/etc/lvm` is restored from the same tarball if
`multipath-tools` touched it.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: both nodes' starting state saved and copied to the Builder
- [ ] Step 2: both downloads complete, no ping missed
- [ ] Step 3: both nodes on 9.3.1, every VM running throughout, the fabric unchanged
- [ ] Step 4: the watcher shows nothing waiting on either node; catalog updated
- [ ] For an Upgrade: `make discover` (`deevnet.mgmt`) run after it, and the Software Catalog updated from its report

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

None yet.

## Follow-ups

- [ ] Each VM picks up the fixed `libzstd` at its next stop and start
