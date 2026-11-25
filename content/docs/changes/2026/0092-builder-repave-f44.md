---
title: "CHG-0092: The Builder Repaved on Fedora 44"
weight: -92
---

# CHG-0092: The Builder Repaved on Fedora 44

| | |
|---|---|
| **Date** | 2026-11-25 |
| **Change type** | Deployment |
| **Classification** | Disruptive |
| **Status** | **Planned** |
| **Window** | 2026-11-25 from 18:30, operator at the Builder's console and near the core router |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (wiped and reinstalled); `dv02bld001v01` (control node and network-boot server for the change); the core router (DNS, DHCP, `next_server`); every host that pins the update watcher's key |
| **Automation** | `deevnet.builder` `site.yml` (tag `grub-mac`, then the whole play on the Builder, then `update_check`); `deevnet.mgmt` `site.yml --tags update_check`; `deevnet.net` `make dns`, `make dhcp` |
| **Risk** | Medium. Most likely to go wrong: the Builder's downloads through the core router hang it (INC-0004, INC-0005). The artifact store is copied from the temporary builder on the management segment instead, and what is left is limited on the Builder itself |
| **Related changes** | [CHG-0091](/docs/changes/2026/0091-temporary-builder-f44/), which built the temporary builder and carried the Builder's work off; [CHG-0042](/docs/changes/2026/0042-rehome-stray-vms/), whose archive the repave releases |
| **Related incidents** | [INC-0004](/docs/incidents/2026/0004-core-router-lost/), [INC-0005](/docs/incidents/2026/0005-core-router-hang-during-rebuild/), [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/) |
| **Related runbooks** | [Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/), [Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/), [Inventory Lifecycle](/docs/runbook/substrate/lifecycle/inventory-lifecycle/) |

---

## Summary

**The Builder, `dv00bld001p01`, is wiped and reinstalled on Fedora 44, network-booted from the
temporary builder.** It runs Fedora 43, which reaches end of life on 2026-12-09, and it is repaved
once per Fedora release
([Resiliency](/docs/policies/risk-management/resiliency/#rebuilds-are-exercised-on-a-schedule)).
CHG-0091 built the temporary builder, `dv02bld001v01`, on Fedora 44 by the same path, and carried
everything the install destroys off the Builder to it. This change follows
[Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/) from its Step 2.

The kickstart gives the Builder a 60G `/home`, up from 20G
([Builder Upkeep](/docs/roadmap/site-work/mobile/builder-upkeep/plan/)).

**The artifact store is copied, not fetched.** CHG-0091 showed that the `artifacts` role can fetch
all of it, about 30G, from upstream. Here it is copied from the temporary builder over the
management segment, which does not cross the core router, and the role then finds it in place. The
Builder is hardware, so there is no hypervisor NIC limit for what it still fetches: a `tc` limit on
its upstream NIC takes that place.

**The Builder's copy of the `pve1` backups is not kept.** CHG-0042 left the two stray VMs' archives
in the Builder's `/srv/pve1-vm-backups`. `dv02hyp001p01`'s upgrade to Proxmox VE 9 has run well
since, so they were not carried off, and the install deletes them.

## Goal

- `dv00bld001p01` runs Fedora 44, installed from `builder-node-44.ks`, with its packages current.
- `df -h /home` on it shows about 60G.
- `deevnet.builder` `site.yml --limit dv00bld001p01` completes from the temporary builder.
- The **Artifact server** and **PXE infrastructure** checks in
  [Verify Site](/docs/runbook/substrate/building-recovery/build-verification/) pass against the
  Builder, and `artifacts` and `pxe` resolve to it again.
- The Builder is the control node again: a play run from it reaches the hosts, the update watcher's
  new key is pinned on every host, and `make discover` runs from it.
- `/opt/omada-controller-backup` on the Builder holds the Omada snapshot copy, with its checksums.

## Scope

**In scope:**
- network boot moved to the temporary builder and back;
- the Builder's install and configuration;
- its setup as the operator's control node;
- the temporary builder made inactive again, once nothing on it is needed.

**Out of scope:**
- moving Podman's storage and `GOPATH` to `/srv`;
- Fedora 45, which the whole site moves to later;
- the follow-ups CHG-0091 found (check mode, false changes, the guest agent).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A bulk download through the core router hangs it | Step 6's package update; Step 7's fetches | The artifact store copied in on the management segment first (Step 5); the Builder's upstream NIC limited to 40 Mbit/s from Step 6 to Step 8; operator at the router's console; the watchdog from CHG-0091 pinging `10.20.25.1` (`10.20.99.1` never answers ping) |
| The copy loads the management hypervisor's disk | Step 5 reads about 30G from `dv02bld001v01`'s disk on `dv02hyp001p01`, where `dv02prv001v01` panicked under load (INC-0006) | `rsync --bwlimit=20000`, the 20 MB/s CHG-0091's copy ran at |
| Work still on the Builder is lost | Step 4 wipes every disk | CHG-0091 carried everything off and checked it; the inventory's vaults are sealed; Step 4 looks once more first |
| The site has no network-boot server, or two | Steps 1–9: `next_server`, the CNAMEs and DHCP point at the temporary builder | Step 2 checks the chain before the Builder boots; Step 9 hands it all back and checks it |
| The Builder reinstalls itself on its next network boot | Its MAC-pinned GRUB config | Step 4 sets its firmware to boot from disk first, and Step 9 removes the entry |
| The update watcher's key changes | The rebuilt Builder makes a new one; every host pins the old one until `update_check` runs | Step 7 skips `update_check`, which reads the key on the control node; Step 10 runs it from the Builder on every host |
| A builder-collection run reaches the wrong builder | Every builder group holds both hosts | Every run passes `--limit` |

## Prerequisites

- [x] CHG-0091 complete: the temporary builder built, and the Builder's work carried to it
- [ ] Inventory pull request for Step 1 merged, and pulled on the temporary builder
- [ ] Operator at the Builder's console, and near the core router's, from Step 2

## Procedure

Every command runs on the temporary builder, `dv02bld001v01`, the control node for this change,
unless a step says otherwise.

### Step 1: Point network boot at the temporary builder in inventory

One pull request, as Repave the Builder's Step 2 lists:

1. `host_vars/dv00bld001p01.yml`, `env.interfaces.eth0`: `pxe_boot.tftp_server: "10.20.99.97"`,
   `pxe_boot.boot_file: "grubx64.efi"`; the `artifacts` and `pxe` CNAMEs move to `dv02bld001v01`.
2. `group_vars/bootstrap_nodes.yml`: a `bootstrap_grub_mac_configs` entry for `dv00bld001p01`, a
   copy of `dv02bld001v01`'s with the Builder's `eth0` MAC.

**Verify:** the pull request is merged, and pulled on the temporary builder.

**Undo:** [Undo Step 1](#undo-steps-1-and-2)

### Step 2: Apply it

```bash
cd ansible-collection-deevnet.net
make dns
make dhcp

cd ../ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit dv02bld001v01 --tags grub-mac
```

`make dns` and `make dhcp` prompt for the vault password at the end; the operator runs them. Then,
by hand on the core router, set the management subnet's `next_server` to `10.20.99.97`.

**Verify:**

1. `dig +short artifacts.mobile.deevnet.net` gives `dv02bld001v01`.
2. `curl -I http://artifacts.mobile.deevnet.net/kickstart/builder-node-44.ks` answers `200` from it.
3. The temporary builder's TFTP root has `grub.cfg-` files for the Builder's MAC.

**Undo:** [Undo Step 1](#undo-steps-1-and-2)

### Step 3: Start the watchdog

Start `migration-logs/chg0091/watchdog.sh` on the temporary builder, with the operator at the
router's console. On three missed pings it takes the Builder's upstream link down.

**Verify:** its log shows replies from `10.20.25.1`.

### Step 4: Network-boot the Builder

Last look on the Builder: `git status` clean in every `/srv/dvnt` checkout, and nothing new under
`/srv` or `/home` since CHG-0091's copy. Then reboot it, and on its console choose a **UEFI**
network boot from `enp4s0`. The install comes from the temporary builder on the management
segment. Once it reboots, set its firmware to boot from disk first.

**Verify:**

1. `ssh a_autoprov@10.20.99.95` answers, and `cat /etc/fedora-release` says 44.
2. `df -h /home /srv`: about 60G for `/home`.

**Undo:** no undo. From here the Builder's old system is gone; the way forward is the rest of
this change, or [Build the Builder](/docs/runbook/substrate/building-recovery/build-the-builder/).

### Step 5: Copy the artifact store in

From the temporary builder, on the management segment:

```bash
rsync -aH --bwlimit=20000 --rsync-path="sudo rsync" \
  --exclude=/deevnet-artifacts-stage \
  /srv/deevnet-http/ a_autoprov@10.20.99.95:/srv/deevnet-http/
```

Owners are mapped by name, not number. The `artifacts` role's checks find each file in place:
the ISOs and netboot files by name and checksum, and the install tree's `rsync --delete` only
checks it against upstream.

**Verify:** `du -sh /srv/deevnet-http` matches on both hosts, and the ISOs' `sha256sum` match.

### Step 6: Limit the Builder's upstream NIC, and bring its packages up to date

On the Builder, the device `ip route get 1.1.1.1` names, `<up>`:

```bash
sudo tc qdisc add dev <up> handle ffff: ingress
sudo tc filter add dev <up> parent ffff: matchall action police rate 40mbit burst 256k drop
sudo dnf upgrade --refresh -y
sudo reboot
```

The limit does not survive the reboot: set it again with the same two `tc` lines.

**Verify:**

1. `tc -s filter show dev <up> ingress` shows the `police` action, after the reboot too.
2. `rpm -q kernel` lists a newer kernel than the media's, and it is the one running.

**Undo:** `sudo tc qdisc del dev <up> ingress`.

### Step 7: Apply the builder configuration

```bash
cd ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit dv00bld001p01 --skip-tags update_check
```

`update_check` reads the watcher's public key on the control node, and the temporary builder has
none; it runs from the Builder in Step 10. The `update_watch` role makes the rebuilt Builder's new
key.

**Verify:**

1. The play completes with `failed=0`; a second run changes only what CHG-0091 found reports a
   change without making one.
2. The `tc` limit is still on `<up>` after the play.

**Undo:** no undo; Step 4 again rebuilds the Builder.

### Step 8: Lift the limit

On the Builder: `sudo tc qdisc del dev <up> ingress`. Stop the watchdog.

**Verify:** `tc qdisc show dev <up>` lists no `ingress`.

### Step 9: Hand network boot back

1. Revert the Step 1 pull request, in a new one: `pxe_boot` back to `10.20.99.95` and
   `pxelinux.0`, the CNAMEs back on `dv00bld001p01`, the Builder's `grub-mac` entry removed.
2. `make dns` and `make dhcp`; the `grub-mac` tag with `--limit dv02bld001v01`, and the Builder's
   leftover `grub.cfg-*` files on the temporary builder deleted.
3. `next_server` back to `10.20.99.95` by hand on the router.

**Verify:** `dig +short artifacts.mobile.deevnet.net` gives `dv00bld001p01`, and
`curl -I http://artifacts.mobile.deevnet.net/kickstart/builder-node-44.ks` answers `200` from it.

### Step 10: Make the Builder the control node again

On the Builder, as the operator:

1. Log in once from a terminal and set the dev user's password (its starting one is expired).
2. Clone the Deevnet repositories into `/srv/dvnt`, then `make publish` in
   `ansible-collection-deevnet.net` and `ansible-collection-deevnet.builder`.
3. `known_hosts` by name: `ssh-keyscan` each host, and keep the keys that match the ones the
   temporary builder holds.
4. Pin the watcher's new key everywhere:
   ```bash
   cd ansible-collection-deevnet.builder
   ansible-playbook playbooks/site.yml --tags update_check
   cd ../ansible-collection-deevnet.mgmt
   ansible-playbook playbooks/site.yml --tags update_check
   ```
5. The patch tools: `make patch-mcp-register` in `ansible-collection-deevnet.builder`, then
   `make update-watch-now`.
6. The Omada snapshot copy back into `/opt/omada-controller-backup`, from the temporary builder's
   `/srv/builder-carry/omada-controller-backup`, with its checksums.
7. Whatever else the operator wants back from `/srv/builder-carry`, the other `/srv` projects, and
   the operator's tools (`gh auth login`, the `cd` plugin, Claude's memory from the temporary
   builder).

All of it crosses the management segment only, apart from the clones.

**Verify:**

1. `ansible-playbook playbooks/site.yml --check --limit dv02bld001v01 --tags operator-env` from the
   Builder passes.
2. `make update-watch-now` reports every host, with no login failures.
3. `sha256sum -c` passes in `/opt/omada-controller-backup`.

### Step 11: Make the temporary builder inactive again

Only once the operator says nothing more is needed from `/srv/builder-carry`:

1. `qm stop 202` and `qm destroy 202 --purge` on `dv02hyp001p01`.
2. Inventory pull request: `dv02bld001v01` back in `inactive`, and `10.20.99.97/32` out of
   `openbao_ansible_cidrs`; then `make dns` and `make dhcp`
   ([Inventory Lifecycle → Inactive hosts](/docs/runbook/substrate/lifecycle/inventory-lifecycle/#inactive-hosts)).

**Verify:** `dig +short dv02bld001v01.mobile.deevnet.net` gives nothing.

## Verification

Every line of the [Goal](#goal), and Verify Site's **Artifact server** and **PXE infrastructure**
checks against `dv00bld001p01`.

## Undo

Until Step 4 the Builder is untouched, and the undo puts network boot back. After Step 4 there is
no going back to Fedora 43: the way forward is the rest of this change.

### Undo Steps 1 and 2

Revert the Step 1 pull request, run `make dns`, `make dhcp` and the `grub-mac` tag, and set
`next_server` back to `10.20.99.95` by hand.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: inventory pull request
- [ ] Step 2: network boot on the temporary builder
- [ ] Step 3: watchdog
- [ ] Step 4: the Builder installed
- [ ] Step 5: artifact store copied in
- [ ] Step 6: limit set, packages current
- [ ] Step 7: builder configuration
- [ ] Step 8: limit lifted
- [ ] Step 9: network boot handed back
- [ ] Step 10: the Builder the control node again
- [ ] Step 11: the temporary builder inactive again
- [ ] Verification: Goal and Verify Site
- [ ] `make discover` from the Builder, and the Software Catalog's Builder row updated from its report
- [ ] Builder Upkeep: the `/home` task done, and its waypoint split, `/home` done and the build caches under `/srv` still planned
- [ ] Repave the Builder updated from this change's Outcome: the artifact store copied in, the limit on the Builder, `update_check` after, `/srv/discovery` made by hand on a temporary builder
- [ ] Inventory Lifecycle → Inactive hosts: `dv02bld001v01`'s row back in the table

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

### Found along the way
