---
title: "Build Management Plane"
weight: 11
aliases:
  - /docs/runbook/building-recovery/build-management-plane/
---

# Build Management Plane

Install and configure a Proxmox VE hypervisor, from bare metal to a node that automation can build
VMs on. It applies to a new node, and to a rebuild of an existing one. The worked example is the
management hypervisor, `dv02hyp001p01`.

This covers the **hypervisors themselves**. Putting an OS on the VMs that run on top of them is
[Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/).

Everything below comes from inventory or from code, except three manual steps: installing Proxmox
from the ISO, running the first bootstrap script at the console, and creating the API token.

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
  ([Configure PXE](/docs/runbook/substrate/building-recovery/build-sequence/)).
- **The Builder has staged the artifacts:** the Proxmox VE ISO under `isos/proxmox`, and the
  node's bootstrap scripts under `bootstrap/pve/`. The `artifacts` role publishes both.
- **The vault is decrypted** ([Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/)).
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
**Install onto the OS disk.** On a node with a data disk, the installer may offer the data disk
first. Identify the OS disk by the `proxmox_install_disk_serial` recorded in inventory before you
confirm.
{{< /hint >}}

## Step 2: Stage the installer

Write the Proxmox VE ISO the Builder staged under `isos/proxmox` to a USB stick. **Install the
version the node was running**; upgrading is a separate change
([Hypervisor Platform Uplift](/docs/roadmap/infrastructure/mobile/hypervisor-uplift/)).

{{< hint info >}}
`deevnet-image-factory` has an unattended ISO build (`make proxmox-pve-iso-ext4`) with the settings
below in an embedded answer file. It is unfinished and has not installed either node, so the
install is manual. Finishing it is on the [Builder roadmap](/docs/roadmap/infrastructure/mobile/builder/).
{{< /hint >}}

## Step 3: Install (manual)

Boot the USB stick and run the graphical installer with these settings. They reproduce
`dv02hyp001p01`'s OS disk:

| Setting | Value |
|---|---|
| Target disk | The OS disk, identified by `proxmox_install_disk_serial` — never the data disk |
| Filesystem | ext4 |
| `swapsize` | 8 GB |
| `minfree` | 16 GB left free in the volume group |
| `hdsize`, `maxroot`, `maxvz` | Installer defaults |
| Hostname (FQDN) | The inventory name, e.g. `dv02hyp001p01.mobile.deevnet.net`. **A Proxmox node is not safely renamable afterwards** |
| Network | Whatever the installer detects. Step 4 replaces it from inventory |

The node reboots into Proxmox.

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

## Step 7: Proxmox access (token manual)

The roles, users and ACLs automation uses on each node are declared in inventory
(`proxmox_node_access` in the node's `vars.yml`) and applied by the `proxmox_node_access` role in
`deevnet.builder`. Only the API tokens are made by hand: a token's secret is shown once, so the role
verifies tokens and never creates them.

| Node | Token | Stored in | Used by |
|---|---|---|---|
| `dv02hyp001p01` | `terraform-prov@pve!tf-prov-token` | `host_vars/dv02hyp001p01/vault.yml` | Packer builds, through `pve-creds` |
| `dv02hyp002p02` | `terraform-prov@pve!terraform-prov-token` | `host_vars/dv02hyp002p02/vault.yml` | Packer builds and the tenant fabric |
| `dv02hyp002p02` | `deevnet-api@pve!tenants` | `group_vars/deevnet_api/vault.yml` | The Deevnet API |

1. **Apply the declaration:**
   ```bash
   cd ansible-collection-deevnet.builder
   ansible-playbook playbooks/site.yml --limit <node> --tags proxmox-access
   ```
   It creates the roles and users, then stops at the first missing token and names it.
2. **Issue each missing token**, as root on the node, with privilege separation on (the default):
   ```bash
   pveum user token add terraform-prov@pve tf-prov-token
   ```
   Put the printed secret into its vault file straight away, then `make vault`, commit and **push**
   before doing anything else.
3. **Apply again.** With the tokens present, the role grants their ACLs. With privilege separation,
   *"effective permissions are calculated by intersecting user and token permissions"*, so both the
   user and the token hold each grant.
4. **Hand the tokens to what uses them:** `ansible-playbook playbooks/site.yml --tags openbao` in
   `deevnet.mgmt` for the build token, which the builds read from OpenBao
   ([Build-Time Secrets](/docs/runbook/substrate/building-recovery/build-secrets/)), and
   `--limit deevnet_api` for the API's.

Not declared, and not recreated: the user `packer-prov@pve` on `dv02hyp001p01`, which has
`Administrator` at `/` and no token.

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
   template directly onto the node, fetching its credentials per run
   ([Build-Time Secrets](/docs/runbook/substrate/building-recovery/build-secrets/)). If OpenBao isn't
   rebuilt yet, prefix it with `PVE_CREDS_SOURCE=inventory`.
2. **Orphaned volumes.** If the data disk survived, the old VMs' volumes are still in `vgbigdata`,
   and `lvs vgbigdata` lists them (`vm-<vmid>-disk-N`). Decide what to keep before rebuilding.
   A rebuilt VM gets new volumes. `lvremove` an orphan only once you're sure nothing on it is
   needed.
3. **VMs.** Follow [Allocate VM Identity](/docs/runbook/substrate/building-recovery/vm-identity/) and
   [Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/). Allocated
   VMIDs are kept in inventory, so each VM gets back the same MAC and address.

## Verify

- `ssh a_autoprov@dv02hyp001p01.mobile.deevnet.net 'sudo -n pveversion'` reports the installed
  version.
- `make vm-identity` in `deevnet.mgmt` reaches the node and reports no collision.
- Every storage the inventory declares is active, and a management VM builds and answers at its
  address.
