---
title: "Build Management Plane"
weight: 11
---

# Build Management Plane

Install and configure a Proxmox VE hypervisor, from bare metal to a node that automation can build
VMs on. It applies to a new node, and to a rebuild of an existing one. The worked example is the
management hypervisor, `dv02hyp001p01`.

This covers the **hypervisors themselves**. Putting an OS on the VMs that run on top of them is
[Build a Management-Plane VM](/docs/runbook/building-recovery/build-management-vm/).

Everything below comes from inventory or from code, except three manual steps: booting the ISO,
running the first bootstrap script at the console, and creating the API token.

---

## Prerequisites

- **The node is declared in inventory** (`host_vars/<node>/vars.yml`):
  - the management NIC's MAC and address
  - `proxmox_node`
  - `proxmox_install_disk_serial`
  - `proxmox_node_storage`, for nodes with a data disk
  - `proxmox_node_network`
- **The network answers on the management VLAN.** Either the core router serves the node's DHCP
  reservation, or the Builder is in bootstrap-authoritative mode
  ([Configure PXE](/docs/runbook/building-recovery/build-sequence/)).
- **The Builder has staged the artifacts:** the Proxmox VE ISO under `isos/proxmox`, and the
  node's bootstrap scripts under `bootstrap/pve/`. The `artifacts` role publishes both.
- **The vault is decrypted** ([Vault Operations](/docs/runbook/building-recovery/vault-operations/)).
- **A console:** monitor and keyboard on the node.

---

## Step 1: Decide what survives

A node's disks have different owners, and a rebuild treats them differently.

| Disk (`dv02hyp001p01`) | Holds | On an OS reinstall |
|---|---|---|
| OS disk, 476.9G | Proxmox, `/etc/pve` (storage entries, guest definitions, API tokens), `local-lvm` | Wiped |
| Data disk, 1.8T, volume group `vgbigdata` | Thin pool `bigthin` (`local-lvm-big-thin`): the template and the management VMs' disks. Thick volumes (`local-lvm-big`): VM 104 | Untouched, if the installer is pinned to the OS disk |

- **If only the OS disk is lost,** the VM disks survive, but their definitions in `/etc/pve` do
  not. Management VMs are rebuilt from code (Step 9). Their old volumes remain on the data disk
  as orphans until they're removed.
- **If the data disk is lost,** Step 6 recreates its volume group and pool empty, and everything
  on it is rebuilt from code.
- **`vdvntm-admin-01` (VM 100) and `vdvntm-winox` (VM 104) are not in inventory.** No step here
  recreates them.

{{< hint danger >}}
**Pin the install disk.** Unpinned, the Proxmox installer takes the first disk it finds, and on a
node with a data disk that can be the data disk. The ISO built in Step 2 selects the disk by the
`proxmox_install_disk_serial` recorded in inventory, and the build warns when none is given.
{{< /hint >}}

## Step 2: Build the install ISO

In `deevnet-image-factory`, on the Builder:

```bash
make proxmox-pve-iso-container          # once
make proxmox-pve-iso-ext4 \
    PVE_ISO_VERSION=8.4-1 \
    PVE_HOSTNAME=dv02hyp001p01.mobile.deevnet.net \
    PVE_DISK_SERIAL='SAMSUNG_SSD_PM871b_M.2_2280_512GB_S3TZNB0K409229' \
    PVE_ROOT_PASSWORD_HASH="$(openssl passwd -6)"
```

- **Install the version the node was running.** Upgrading is a separate change
  ([Hypervisor Platform Uplift](/docs/roadmap/infrastructure/mobile/hypervisor-uplift/)).
- **The ext4 answer file reproduces `dv02hyp001p01`'s OS disk:** 8G swap, 16G left free in the
  volume group, and the installer's default root and `data` sizes.
- **The hostname must be the inventory name.** A Proxmox node is not safely renamable afterwards.

**Which serial string to use.** `PVE_DISK_SERIAL` is the disk's udev `ID_SERIAL`, and for a SATA disk
that is model plus serial. It's the `/dev/disk/by-id/ata-…` name with the `ata-` prefix dropped.
`lsblk`'s SERIAL column, `S3TZNB0K409229` here, is the short form and does not match. Proxmox's
example filter is `ID_SERIAL='KIOXIA_KCMYXVUG1T60*'`. To list what the installer sees, run
`proxmox-auto-install-assistant device-info -t disk` inside the container.

## Step 3: Install

Boot the ISO from USB. The install is unattended, and the node reboots into Proxmox.

## Step 4: Network, hostname, resolver (console)

Stage 1 of the bootstrap. It finds the management NIC by its inventory MAC, writes `vmbr0` with
the node's address, and sets the hostname and resolver. The script is at
`http://artifacts.mobile.deevnet.net/bootstrap/pve/dv02hyp001p01-netconfig.sh`.

- If the node already took its DHCP reservation, fetch it with `curl`.
- Otherwise, carry it on a USB stick.

Run as root:

```bash
bash dv02hyp001p01-netconfig.sh
ip -br a show vmbr0 && ping -c2 10.20.99.1
```

## Step 5: Automation account and packages

Stage 2. It switches to the no-subscription repository, creates `a_autoprov` with its key and
passwordless sudo, and installs the packages the platform needs. Run as root:

```bash
curl -fsSL http://artifacts.mobile.deevnet.net/bootstrap/pve/dv02hyp001p01-configure.sh | bash
```

**Verify** from the Builder: `ssh a_autoprov@10.20.99.21 'sudo -n id -un'` prints `root`.

## Step 6: Baseline and storage

In `ansible-collection-deevnet.builder`:

```bash
ansible-playbook playbooks/site.yml --limit dv02hyp001p01
```

The `hypervisors` play runs two roles:
- **`proxmox_node_base`:** it asserts the node name, then sets the loopback/FQDN mapping, the
  resolver and the automation account.
- **`proxmox_node_storage`:** it reads `proxmox_node_storage` from host_vars.
  - **OS disk rebuilt:** LVM already sees `vgbigdata`, so the role only adds the PVE storage entries
    back.
  - **New or replaced data disk:** the role refuses to create a volume group unless the run is
    given `-e proxmox_node_storage_allow_create=true`. Even then it creates one only on a device
    with no existing signature. The partition the device path names must already exist.

**Verify:** `pvesm status` lists `local-lvm-big-thin` and `local-lvm-big` as active.

## Step 7: API token (manual)

Automation authenticates to the Proxmox API as the token `terraform-prov@pve!tf-prov-token`,
recorded in the node's vault as `vault_proxmox_token_id` and `vault_proxmox_token_secret`.

**State as read on 2026-09-14:**
- It is the only API token on `dv02hyp001p01`, with privilege separation on (`privsep 1`).
- `Administrator` at `/` is granted to both the user and the token.

**What a rebuild has to do:**
- **Issue a new token.** Its value can't be recovered from a lost node: Proxmox shows it *"only
  displayed/returned once when the token is generated"*.
- **Grant both ACLs.** With privilege separation, *"effective permissions are calculated by
  intersecting user and token permissions"*. A token granted a role while its user has none can
  do nothing.

As root on the node:

```bash
pveum user add terraform-prov@pve
pveum user token add terraform-prov@pve tf-prov-token      # privilege separation on by default
pveum acl modify / --roles Administrator --users terraform-prov@pve
pveum acl modify / --roles Administrator --tokens 'terraform-prov@pve!tf-prov-token'
```

Put the printed value into `host_vars/dv02hyp001p01/vault.yml` as `vault_proxmox_token_secret`
straight away, then run `make vault`.

**Not recreated:** the node also has a user `packer-prov@pve` with `Administrator` at `/` and no
token. The image factory's Packer builds use the vault token above.

**Follow-up:** both the `terraform-prov` name and `Administrator` at `/` predate the rule that the
management plane is Ansible-only. Narrowing the token is a separate change.

## Step 8: VLAN-aware bridge

In `ansible-collection-deevnet.net`:

```bash
ansible-playbook playbooks/proxmox-node-network.yml --tags interfaces -e target=dv02hyp001p01
```

This makes `vmbr0` VLAN-aware (VIDs 2–4094), so tagged guest NICs reach Platform and IoT Backend.
Management stays untagged.

- **On `dv02hyp001p01`, stop here.** It declares no transit VLAN, so the role's `mgmt-routing`,
  `default-route` and `tenant-egress` tags don't apply.
- **On a tenant hypervisor**, continue with those tags in the order the role's README gives.

**Verify:** `cat /sys/class/net/vmbr0/bridge/vlan_filtering` prints `1`.

## Step 9: Template and VMs

1. **Template.** In `deevnet-image-factory`, run `make proxmox-fedora-pve1`. It builds the Fedora
   template directly onto the node.
2. **Orphaned volumes.** If the data disk survived, the old VMs' volumes are still in `vgbigdata`,
   and `lvs vgbigdata` lists them (`vm-<vmid>-disk-N`). Decide what to keep before rebuilding.
   A rebuilt VM gets new volumes. `lvremove` an orphan only once you're sure nothing on it is
   needed.
3. **VMs.** Follow [Allocate VM Identity](/docs/runbook/building-recovery/vm-identity/) and
   [Build a Management-Plane VM](/docs/runbook/building-recovery/build-management-vm/). Allocated
   VMIDs are kept in inventory, so each VM gets back the same MAC and address.

## Verify

- `ssh a_autoprov@dv02hyp001p01.mobile.deevnet.net 'sudo -n pveversion'` reports the installed
  version.
- `make vm-identity` in `deevnet.mgmt` reaches the node and reports no collision.
- Every storage the inventory declares is active, and a management VM builds and answers at its
  address.
