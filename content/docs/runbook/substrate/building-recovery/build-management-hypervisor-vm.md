---
title: "Build a Management-Hypervisor VM"
weight: 13
aliases:
  - /docs/runbook/building-recovery/build-management-vm/
  - /docs/runbook/substrate/building-recovery/build-management-vm/
---

# Build a Management-Hypervisor VM

Two supported ways to put an OS on a management-hypervisor VM. Both produce a host that is
reachable at its reserved address, carries a deterministic MAC, and can be rebuilt from
its declaration.

| | **Clone from template** | **PXE netboot** |
|---|---|---|
| Source of the OS | Packer-built Proxmox template | Install tree on the artifact server |
| Driven by | `deevnet.mgmt` `roles/proxmox_vm` | `roles/proxmox_vm` (`source: pxe`), then anaconda + `builder-node-<release>.ks` |
| Firmware | SeaBIOS (the template's default) | **UEFI/OVMF** — the kickstart declares an ESP |
| Typical time | 2–5 minutes | 20–40 minutes |
| Use it for | Anything that just needs the current base image | Validating the netboot path, or a host whose disk layout the template cannot produce |

**Clone is the default.** Reach for PXE when the point *is* the PXE path — proving a new
Fedora release installs unattended before pinning any auto-installing host to it — or when
the kickstart's layout (a large `/srv`, separate `/home`) is what you actually want.

---

## Prerequisites (both approaches)

The order below is fixed and **not reorderable**. See
[Allocate VM Identity](/docs/runbook/substrate/building-recovery/vm-identity/).

1. Host declared in `hosts.yml` under `management_plane`, with `host_vars/<host>/vars.yml`
   as a **directory** (the allocator asserts this).
2. `make vm-identity-assign` in `deevnet.mgmt` — writes `identity.yml` with the VMID and
   its derived MAC.
3. **Delete any stale reservation for an address this host will take.** `opnsense_dhcp`
   reconciles by MAC and only ever adds or updates; a host rebuilt under a new MAC leaves
   its old reservation behind, and two reservations for one address is a failure that looks
   like success. See [Declarative Reconciliation](/docs/roadmap/infrastructure/substrate/reconciliation/).
4. `make dhcp && make dns` in `deevnet.net`.
5. Build.

A VM that boots before step 4 takes an address from the DHCP pool instead of its
reservation, and the build fails several minutes later at the reachability check reporting
only that the guest "booted but is not on" its expected address.

---

## Approach A — Clone from template

### Declare

In `host_vars/<host>/vars.yml`, alongside `infrastructure` and `env`:

```yaml
mgmt_vm:
  hypervisor: dv02hyp001p01
  node: dv02hyp001p01
  vmid: "{{ deevnet_assigned_vmid | default(0) }}"
  template_prefix: "fedora-server-"     # matched by prefix, newest wins - never a VMID
  storage: local-lvm-big-thin
  cores: 2
  memory: 4096
  os_disk_size: 64                      # optional; grows the clone before first boot
  data_disk:                            # optional
    device: scsi1
    size: 250
    storage: local-lvm-big-thin
    mount: /srv
```

Keep `infrastructure` at host level, never in a group. Ansible does not hash-merge, so a
group-level `infrastructure` dict is replaced wholesale and `opnsense_dhcp` **silently
stops writing a reservation** for the host.

### Build

```bash
cd ansible-collection-deevnet.mgmt && make rebuild
ANSIBLE_COLLECTIONS_PATH="./.ansible/collections:$HOME/.ansible/collections" \
  ansible-playbook playbooks/site.yml --limit <host>
```

The `ANSIBLE_COLLECTIONS_PATH` is not optional. A bare `ansible-playbook` resolves to the
system-wide collections and silently ignores the project-local build.

### What it does, and what it checks

Clone → set MAC and cloud-init → attach the data disk → read the config back → assert →
grow the OS disk → start → wait for SSH → assert the guest is on its reserved address.

The asserts exist because **an API call reporting `changed` is not evidence**. Each one
catches a failure that would otherwise surface minutes later as an unexplained timeout:

- **net0 carries the declared MAC.** `proxmox_kvm` silently strips `net` from an update
  payload unless `update_unsafe: true` is set, which would leave the clone on the random
  MAC PVE generated and the Kea reservation matching nothing.
- **The data disk is attached with its serial.** Without the serial the guest cannot find
  the disk by a stable path.
- **The guest came up on its reserved address**, not a pool lease.

### Disks

**OS disk** — grown before first boot; cloud-init's `growpart` extends the root filesystem
on that boot. Verify *inside the guest*: `df -h /` must reflect the new size. PVE reporting
64 G while `df` reports 32 G means the resize worked and growpart did not, which looks like
success from the hypervisor side.

**Data disk** — created once and never re-created or resized by the role. Found in the
guest by its serial via `/dev/disk/by-id`, never by `/dev/sdX` (device names are assigned in
discovery order, so a later disk renumbers them). Filesystem is made only if absent, so a
guest reinstalled into the same VMID re-mounts existing data.

> **Scope of the promise.** The data disk survives re-running the play and survives
> replacing the OS disk. It does **not** survive `qm destroy`, which deletes every volume
> the VM owns. "Outlives the VM" means "outlives the OS disk", not "outlives the VMID".

---

## Approach B — PXE netboot

### Extra requirements beyond the shared prerequisites

**1. The VM needs a VirtIO RNG device.** A UEFI VM without one cannot PXE boot at all —
see [Bootstrap Role](/docs/platforms/management-plane/builder-node/bootstrap-role/). This is the
single most common way this approach fails, and it fails silently.

**2. The reservation must specify a UEFI boot file.** In `host_vars`:

```yaml
        pxe_boot:
          tftp_server: "10.20.99.95"
          boot_file: "grubx64.efi"      # not pxelinux.0 - this guest is OVMF
```

**3. The subnet must have `next_server` set.** Not managed by any role. If it is empty,
Kea advertises its own address in `siaddr`, UEFI firmware reads `siaddr` rather than DHCP
option 66, and the client tries to TFTP from the router. The per-host
`option_data.tftp_server_name` looks like it covers this and does not — reservations carry
no `next_server` field.

**4. A MAC-pinned GRUB config, for an unattended install.** Add an entry to
`bootstrap_grub_mac_configs` referencing `hostvars[...].infrastructure.interfaces.eth0.mac`
— never a literal — then:

```bash
cd ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit dv00bld001p01 --tags grub-mac
```

Without an entry the client falls through to the interactive menu and its 30-second
timeout. The role renders **six filename variants** per host because GRUB's
`$net_default_mac` format varies by firmware; OVMF requests the **lowercase-with-colons**
form, so the dashed variants alone are not enough.

### Declare

**`proxmox_vm` creates the empty VM when the host declares `source: pxe`.** In
`host_vars/<host>/vars.yml`:

```yaml
mgmt_vm:
  source: pxe
  hypervisor: dv02hyp001p01
  node: dv02hyp001p01
  vmid: "{{ deevnet_assigned_vmid | default(0) }}"
  storage: local-lvm-big-thin
  cores: 2
  memory: 4096
  os_disk_size: 100        # required; the kickstart needs about 88 GiB
```

No `template_prefix`, `static_ip` or cloud-init settings: anaconda owns the install, on the host's
DHCP reservation.

### Build

```bash
cd ansible-collection-deevnet.mgmt && make rebuild
ANSIBLE_COLLECTIONS_PATH="./.ansible/collections:$HOME/.ansible/collections" \
  ansible-playbook playbooks/site.yml --limit <host> --tags vms
```

The role creates the VM, starts it, and waits up to an hour for SSH on the reserved address, so the
play ends when the installed host answers. The VM it creates:

| Setting | Value | Why |
|---|---|---|
| `bios` | `ovmf` | the kickstart declares `part /boot/efi --fstype=efi` and has no `biosboot`, so a legacy install cannot complete |
| `efidisk0` | `<storage>:1,efitype=4m,pre-enrolled-keys=0` | **Secure Boot must be off**: `grubx64.efi` is built locally by `grub2-mkimage` and is unsigned |
| `rng0` | `source=/dev/urandom` | mandatory; see above |
| `machine` | `q35` | |
| `net0` | `virtio=<mac>,bridge=vmbr0` | the declared MAC, which the reservation and the GRUB config key off |
| `scsi0` | `<storage>:<os_disk_size>` | the kickstart's floor is about 88 GiB (1 G `/boot` + 512 M ESP + 50 G root + 20 G `/home` + 16 G swap) and gives no useful error below it |
| `boot` | `order=scsi0;net0` | **disk first, from the start**: the blank disk falls through to the network, and once installed the disk boots, so it never reinstalls itself |
| cloud-init drive | none | anaconda owns this install |

### The boot chain

Watch it from the artifact server:

```bash
journalctl -u tftp -f                                   # in.tftpd runs -v -v -v
sudo tail -f /var/log/nginx/artifacts.access.log        # NOT access.log - the vhost has its own
```

Expected, in order:

```
DHCP  -> reserved address, siaddr = TFTP server, file grubx64.efi
RRQ grubx64.efi
RRQ /grub.cfg                       (grubx64 is built with prefix (tftp)/grub)
RRQ /grub.cfg-<mac lowercase colons>
RRQ /fedora/<release>/vmlinuz
RRQ /fedora/<release>/initrd.img    (~263 MB; takes a moment)
GET /kickstart/builder-node-<release>.ks
GET /fedora/<release>/mirror/...    anaconda switches to HTTP here
```

### After the install

**The VM boots its disk from then on, with no boot order to change.** Proxmox's boot order is disk
first, so after the install's reboot, a guest reboot or a power cycle, the installed system boots and
the network is never asked. A request for `grubx64.efi` from the host after its install means its
disk is not bootable.

Then remove the host's entry from `bootstrap_grub_mac_configs`, re-run the `grub-mac` tag, and
delete the host's `grub.cfg-*` files by hand: that role renders configs but never prunes them. Left
in place, the entry reinstalls the host, unattended and wiping its disk, the next time its disk will
not boot.

### Finish

The kickstart leaves the host on DHCP with the hostname `builder-node`. Its real identity
and static address are applied afterwards by `base`:

```bash
cd ansible-collection-deevnet.builder
ansible-playbook playbooks/site.yml --limit <host>
```

Check SSH explicitly. The kickstart fetches the `a_autoprov` public key with
`curl ... || true`, so a failed fetch produces an unreachable host that looks like a
healthy install.

---

## Troubleshooting

### The guest emits no DHCP at all

Console shows `BdsDxe: No bootable option or device was found` with no network boot entry.
The firmware has disabled its network stack for lack of entropy — **add
`rng0: source=/dev/urandom`**. Confirm with a capture on the segment
(`tcpdump -i <iface> 'port 67 or port 68 or port 69'`); zero packets over a full boot cycle
is the signature.

Two things this is **not**, both verified by rebuilding the VM from scratch each way:

- **Not the NIC model.** `virtio` and `e1000` fail identically without entropy and both work
  with it.
- **Not stale firmware NVRAM.** A brand-new `efidisk0` behaves the same.

### DHCP works, but no TFTP request follows

`next_server` is empty on the subnet. Check the OFFER's `siaddr` in a capture before
changing anything else.

### TFTP requests arrive, but transfers fail

Check that the files exist on the artifact server, then fetch one by hand from another host on the segment:

```bash
ls -la /srv/tftp/grubx64.efi /srv/tftp/grub.cfg-*
tftp 10.20.99.95 -c get grubx64.efi /tmp/test.efi   # expect about 1.2 MB
```

### It boots the interactive menu instead of installing

The MAC-pinned GRUB config is missing, or the firmware's `$net_default_mac` format has no
matching variant on disk.

### It reinstalls itself on every reboot

The boot order has the network first. A VM created by `proxmox_vm` has the disk first; a VM made by
hand needs `boot: order=scsi0;net0`, and a **power cycle** (stop, then start) to take it: the boot
order is fixed when QEMU starts, so a guest reboot keeps the old one. Stop it between two installs,
not while anaconda writes packages. A round finished when `%post` fetches
`keys/ssh/a_autoprov_rsa.pub` from the artifact server.

### The guest is up but on the wrong address

Its reservation is missing or duplicated. `opnsense_dhcp` skips a host whose MAC is empty
**silently**, so confirm the reservation exists on the core router rather than assuming the
play wrote it.
