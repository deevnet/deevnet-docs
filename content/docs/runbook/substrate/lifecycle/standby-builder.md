---
title: "The Standby Builder"
weight: 4
---

# The Standby Builder

The standby builder, `dv02bld001v01`, is a second builder kept running beside the Builder,
`dv00bld001p01`. **It exists for two jobs the Builder cannot do for itself:** it repaves the Builder,
and it takes a risky change first, so the site's builders change one at a time. It is a VM on the
management hypervisor, built from the same kickstart and configured by the same `deevnet.builder`
roles as the Builder, so what works on it is expected to work on the Builder. It was kept, rather
than destroyed after the Builder's repave, by the operator's decision of 2026-11-27
([CHG-0092](/docs/changes/2026/0092-builder-repave-f44/)).

| | |
|---|---|
| Host | `dv02bld001v01`, VMID 202 on `dv02hyp001p01`, 10.20.99.97, management segment |
| Install | Fedora, from the builder kickstart (`builder-node-<release>.ks`), over the network from the Builder ([CHG-0091](/docs/changes/2026/0091-temporary-builder-f44/)) |
| Configuration | `deevnet.builder` `site.yml`, as on the Builder: it is in the same `builder`, `artifact_servers`, `bootstrap_nodes` and `workstations` groups |
| Not on it | The update and health watchers and Claude's patch tools (`update_watchers` is the Builder alone) |
| Watched by | The Builder's health watcher ("`dv02bld001v01` answers") and update watcher |

---

## Repaving the Builder

**The Builder is the one host that cannot network-boot itself, so the standby builder does it.**
During a repave it is the control node and the network-boot server: DHCP's `next_server` and the
`artifacts` and `pxe` names point at it, it serves the kickstart and the install tree, and it applies
the builder configuration to the new Builder. The procedure is
[Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/).

**The Builder is never repaved without it.** If the standby builder is gone, it is built again first,
from the Builder, as in CHG-0091. If the Builder is already gone too,
[Build the Builder](/docs/runbook/substrate/building-recovery/build-the-builder/) starts from a bare
machine instead.

## One builder at a time

**A change that could leave a builder unusable is made on the standby builder first, and on the
Builder only once the standby builder has worked with it.** While one builder is being changed, the
other is a working control node, so a change that goes wrong never leaves the site without a way to
run its plays, reach its hosts or rebuild.

**Risky changes take the standby builder in one change record and the Builder in a later one**, with
the standby builder in use in between:

- a Fedora release upgrade (as opposed to updates within a release);
- a change to the `deevnet.builder` roles every builder runs (`base`, `workstation`, `artifacts`,
  `bootstrap`), or to their pinned dependencies (`ansible-core`, the collections in
  `requirements.yml`);
- a new major version of the operator's tools (Claude Code, Podman, Terraform);
- anything a change record's Risk row names as able to break the control node.

"In use" means at least: `deevnet.builder` `site.yml --check --limit dv02bld001v01` from the standby
builder itself shows no unexpected change, a play against a real host completes from it, and the
change's own checks pass on it. A change record may ask for more, such as a day of ordinary use.

**Routine patches take both builders in the same change record, the standby builder first.** Updates
within a Fedora release are patched with the service VMs ([Patching](/docs/runbook/substrate/lifecycle/patching/)):
the standby builder before the Builder, and the Builder's reboot last.

**A change to the Builder is run from the standby builder.** The Builder's reboot then ends no
session, and if the Builder does not come back, the operator is already on a working control node.
CHG-0094 ran from the Builder and had to leave its reboot to the operator, which this avoids.

**Before a risky change, the standby builder gets a snapshot; the Builder cannot.** It is a VM:
`qm snapshot 202 <name> --vmstate 0` on `dv02hyp001p01` gives it a way back that the Builder, on
bare metal, does not have. That is one more reason it goes first. The snapshot is dropped once the
change is over, as in [CHG-0094](/docs/changes/2026/0094-patch-builder-service-vms/).

**What the standby builder cannot prove.** It is a VM, so the Builder's own hardware is not tested on
it: its firmware, its NICs and their drivers, its disks, and anything that depends on them, such as
network boot from `enp4s0`. A change to those is planned for the Builder alone, with
[Build the Builder](/docs/runbook/substrate/building-recovery/build-the-builder/) as its way back.

## Keeping it ready

**The standby builder is only useful if it can take over today.** Between uses:

- **Its packages are patched with every cycle**, before the Builder's. The update watcher lists it
  with the Builder.
- **It answers.** The Builder's health watcher raises it if it stops.
- **Its QEMU guest agent runs**, so Proxmox can shut it down cleanly. The builder kickstart installs it.

**Before it serves**, as a control node, for a repave, or for a risky change, it is brought current:

1. Its packages updated, within its Fedora release.
2. Its checkouts in `/srv/dvnt` pulled to `main`, with nothing left uncommitted from a previous use.
3. `make publish` in each collection (`deevnet.builder`, `deevnet.net`, `deevnet.mgmt`), so plays
   that use another collection's roles find the current one.
4. `ssh-add -l` showing the operator's keys: the agent is forwarded to the standby builder by name.

## What is not done yet

**Its disk is not on the VM hardware profile.** It is on `virtio-scsi-pci` without [ADR-0046](/docs/architecture/decisions/substrate/0046-vm-hardware-profile/)'s
`iothread`, `discard` and `cache` settings, acceptable while it was to be destroyed; moving it is a
follow-up in CHG-0092.
