---
title: "Repave the Builder"
weight: 20
---

# Repave the Builder

Reinstall the hardware Builder, `dv00bld001p01`, from scratch. It is the one host that cannot
network-boot itself, so a second builder does it: a temporary builder VM on the management hypervisor
stands in for the Builder, network-boots it with the builder kickstart, and then applies the full
builder configuration to it.

**This is the planned path, for a Builder that is still there to help.** The temporary builder is
cloned from a template on the management hypervisor. If the Builder is already gone, or that
hypervisor or its template is, start from a bare machine instead:
[Build the Builder](/docs/runbook/substrate/building-recovery/build-the-builder/).

| | |
|---|---|
| Temporary builder | `dv02bld001v01`: a management-hypervisor VM on `dv02hyp001p01`, 10.20.99.97, with a 250G data disk at `/srv` |
| Target | `dv00bld001p01`: the AOOSTAR N1 PRO, 10.20.99.95, management NIC `enp4s0` (inventory `eth0`) |
| Install | Fedora, from the builder kickstart (`builder-node-<release>.ks`), over UEFI PXE |
| Configuration | `deevnet.builder` `site.yml`: `base`, `workstation`, `artifacts`, `bootstrap` |

The Builder is repaved once per Fedora release, as part of the scheduled rebuilds that
[Resiliency](/docs/policies/risk-management/resiliency/#rebuilds-are-exercised-on-a-schedule)
requires, and whenever it is lost. This is how the Builder in service was built: over PXE, from the builder VM. The network-boot
mechanics it shares with any PXE build, and their failure modes, are in
[Build a Management-Hypervisor VM → Approach B](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/#approach-b--pxe-netboot).

---

## Before you start: what the install destroys

The kickstart runs `clearpart --all`, so **every disk in the Builder is wiped**. Nothing on it
survives unless you move it off first:

| On the Builder | What to do |
|---|---|
| `/srv/dvnt` checkouts | Re-encrypt every vault (`make vault` in the inventory), then commit and push every branch. Local-only work is lost |
| Other work under `/srv` and `/home` | Copy off anything not in a remote repository |
| `/opt/omada-controller-backup` | The off-host copy of the Omada snapshot ([Omada Controller Recovery](/docs/runbook/substrate/recovery/omada-controller-recovery/)); the original is on `dv02nms001v01`. The cold-fallback controller in `/opt/omada-controller` is empty, and nothing in it needs keeping |
| `/srv/dvnt/migration-logs` | The router's saved `config.xml` copies, written before each firewall apply: the fastest way to [rebuild the core router](/docs/runbook/substrate/recovery/rebuild-core-router/). They hold the router's secrets, so keep them somewhere private |
| `/srv/deevnet-http` (artifacts) | Nothing. The `artifacts` role stages them again, which needs internet access |

Two things are **not** on the Builder: the operator's SSH key is forwarded from their own
machine, and the vault password is typed at each run.

While the Builder is down, the temporary builder is the site's Ansible control node: automation runs
from it, and you reach it from a machine on the trusted segment.

---

## Step 1: Stand up the temporary builder

`dv02bld001v01` is declared in inventory, with its identity allocated (VMID 202). Build it as a
management-hypervisor VM by template clone
([Build a Management-Hypervisor VM → Approach A](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/#approach-a--clone-from-template)),
then clone the repositories into `/srv/dvnt` on it and apply the builder roles to it alone:

```bash
cd ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit dv02bld001v01
```

That stages the artifacts (install tree, kickstarts, the `a_autoprov` public key) under `/srv` and
starts its TFTP server. Always pass `--limit`: every builder group also contains the Builder.

---

## Step 2: Point network boot at the temporary builder

In inventory:

1. **`host_vars/dv00bld001p01.yml`**, `env.interfaces.eth0`:
   - `pxe_boot.tftp_server: "10.20.99.97"`
   - `pxe_boot.boot_file: "grubx64.efi"`. The kickstart only lays out a UEFI system (`/boot/efi`,
     no `biosboot`), so the Builder must network-boot in UEFI mode. Inventory's usual value,
     `pxelinux.0`, is the legacy BIOS loader.
   - Move the `artifacts` and `pxe` entries of `dns.cnames` to `dv02bld001v01`. The kickstart and
     the install tree are fetched through `artifacts.mobile.deevnet.net`.
2. **`group_vars/bootstrap_nodes.yml`**: add a `bootstrap_grub_mac_configs` entry for
   `dv00bld001p01`. Copy the existing entry, with the MAC taken from
   `hostvars['dv00bld001p01'].infrastructure.interfaces.eth0.mac`.

Apply it:

```bash
cd ansible-collection-deevnet.net
make dns
make dhcp

cd ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit dv02bld001v01 --tags grub-mac
```

Then, **by hand on the core router**, set the management subnet's `next_server` to `10.20.99.97`.
No role manages it, and UEFI firmware reads it rather than option 66
([Bootstrap Role → Subnet-Level Settings](/docs/platforms/management-plane/builder-node/bootstrap-role/#subnet-level-settings)).

Check before booting anything: `dig +short artifacts.mobile.deevnet.net` resolves to
`dv02bld001v01`, and `curl -I http://artifacts.mobile.deevnet.net/kickstart/` answers from it.

---

## Step 3: Network-boot the Builder

On the Builder's console, choose a **UEFI** network boot from `enp4s0`, the management NIC. Watch
the boot chain on the temporary builder, as in
[The boot chain](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/#the-boot-chain).
The install is unattended and ends with the host fetching `keys/ssh/a_autoprov_rsa.pub`.

**Stop it reinstalling.** The MAC-pinned GRUB config boots straight into the install, so before the
Builder's next network boot, either set its firmware to boot from disk first, or remove its
`bootstrap_grub_mac_configs` entry, re-run the `grub-mac` tag and delete its leftover `grub.cfg-*`
files on the temporary builder
([Pin the boot order](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/#pin-the-boot-order--do-not-skip-this)).

The installed host comes up on its DHCP reservation, `10.20.99.95`, with the hostname
`builder-node`. Confirm `ssh a_autoprov@10.20.99.95` works; a failed key fetch leaves a host that
looks healthy and cannot be reached.

---

## Step 4: Apply the full builder configuration

From the temporary builder:

```bash
cd ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit dv00bld001p01
```

This applies `base` (identity, static address), `workstation` (operator accounts and tools),
`artifacts` (stages everything again, from the internet over its upstream NIC) and `bootstrap`
(TFTP only; dnsmasq stays off). It does **not** recreate the Omada cold fallback: the Builder is not
in `network_controllers` unless it has been put back there for a recovery.

---

## Step 5: Hand network boot back

1. Revert the Step 2 inventory edits: `pxe_boot` back to `10.20.99.95` and its previous boot file,
   the `artifacts` and `pxe` CNAMEs back on `dv00bld001p01`, and the `grub-mac` entry removed.
2. Apply them with `make dns` and `make dhcp` in `deevnet.net`.
3. Set the subnet's `next_server` back to `10.20.99.95` by hand.
4. Clone the repositories into `/srv/dvnt` on the Builder, and put back anything carried off.
5. Shut down `dv02bld001v01`. It stays declared, for the next repave.

---

## Verify

- `ssh a_autoprov@dv00bld001p01.mobile.deevnet.net` works.
- The **Artifact server** row and the **PXE infrastructure** checks in
  [Verify Site](/docs/runbook/substrate/building-recovery/build-verification/) pass against the
  Builder.
- `dig +short artifacts.mobile.deevnet.net` resolves to `dv00bld001p01` again.
