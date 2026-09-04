---
title: "Build a Management-Plane VM"
weight: 13
---

# Build a Management-Plane VM

Two supported ways to put an OS on a management-plane VM. Both produce a host that is
reachable at its reserved address, carries a deterministic MAC, and can be rebuilt from
its declaration.

| | **Clone from template** | **PXE netboot** |
|---|---|---|
| Source of the OS | Packer-built Proxmox template | Install tree on the artifact server |
| Driven by | `deevnet.mgmt` `roles/proxmox_vm` | anaconda + `builder-node-<release>.ks` |
| Firmware | SeaBIOS (the template's default) | **UEFI/OVMF** — the kickstart declares an ESP |
| Typical time | 2–5 minutes | 20–40 minutes |
| Use it for | Anything that just needs the current base image | Validating the netboot path, or a host whose disk layout the template cannot produce |

**Clone is the default.** Reach for PXE when the point *is* the PXE path — proving a new
Fedora release installs unattended before pinning any auto-installing host to it — or when
the kickstart's layout (a large `/srv`, separate `/home`) is what you actually want.

---

## Prerequisites (both approaches)

The order below is fixed and **not reorderable**. See
[Allocate VM Identity](/docs/runbook/building-recovery/vm-identity/).

1. Host declared in `hosts.yml` under `management_plane`, with `host_vars/<host>/vars.yml`
   as a **directory** (the allocator asserts this).
2. `make vm-identity-assign` in `deevnet.mgmt` — writes `identity.yml` with the VMID and
   its derived MAC.
3. **Delete any stale reservation for an address this host will take.** `opnsense_dhcp`
   reconciles by MAC and only ever adds or updates; a host rebuilt under a new MAC leaves
   its old reservation behind, and two reservations for one address is a failure that looks
   like success. See [Declarative Reconciliation](/docs/roadmap/infrastructure/dvntm/reconciliation/).
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
  hypervisor: hv01
  node: pve
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
see [PXE Role](/docs/platforms/management-plane/bootstrap-node/pxe-role/). This is the
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
ansible-playbook playbooks/site.yml --limit provisioner-ph01 --tags grub-mac
```

Without an entry the client falls through to the interactive menu and its 30-second
timeout. The role renders **six filename variants** per host because GRUB's
`$net_default_mac` format varies by firmware; OVMF requests the **lowercase-with-colons**
form, so the dashed variants alone are not enough.

### Create the VM shell

There is no role for "create an empty VM to PXE boot" — `proxmox_vm` only clones templates.
Create it against the PVE API with:

| Setting | Value | Why |
|---|---|---|
| `bios` | `ovmf` | the kickstart declares `part /boot/efi --fstype=efi` and has no `biosboot`, so a legacy install cannot complete |
| `efidisk0` | `<storage>:1,efitype=4m,pre-enrolled-keys=0` | **Secure Boot must be off** — `grubx64.efi` is built locally by `grub2-mkimage` and is unsigned |
| `rng0` | `source=/dev/urandom` | mandatory; see above |
| `machine` | `q35` | |
| `net0` | `virtio=<mac>,bridge=vmbr0,firewall=0` | virtio is correct here; see the note below |
| `scsi0` | `<storage>:100` | the kickstart's floor is ~88 GiB (1 G `/boot` + 512 M ESP + 50 G root + 20 G `/home` + 16 G swap) and gives no useful error below it |
| `boot` | `order=net0;scsi0` | net first to install — **must be flipped afterwards** |
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

### Pin the boot order — do not skip this

`grub.cfg-mac.j2` renders `set timeout=0` with a single install entry, and the VM boots
`net0` first. Until the boot order is flipped, **every subsequent reboot silently
reinstalls the machine.**

Set `boot: order=scsi0;net0`. Two things about *how*, both learned the hard way:

**A guest reboot does not re-read PVE's boot order.** `bootindex` is fixed when QEMU
starts, so changing `boot:` on a running VM has no effect until the VM is **power cycled**
(stop then start — not `reboot` from inside, and not the PVE "Reboot" button).

**There is a safe window for that stop, and it is about a minute wide.** A looping VM
alternates between installing and rebooting. Stopping it mid-install, while anaconda is
writing packages, leaves a half-written disk on top of the previous complete install. Stop
it *after* one install finishes and *before* the next starts writing:

```bash
# an install completed when %post fetches the key:
grep "<ip>.*keys/ssh" /var/log/nginx/artifacts.access.log | tail -1
# the next round is writing once new .rpm GETs appear:
grep "<ip>.*\.rpm" /var/log/nginx/artifacts.access.log | tail -1
```

Stop when the `keys/ssh` timestamp is newer than the last `.rpm` timestamp.

**Diagnosing the loop.** Repeated installs look like repeated *failures* — same package
count, same cadence, never finishing. The discriminator is whether `%post` ran: the
kickstart fetches `keys/ssh/a_autoprov_rsa.pub` at the very end, so a hit on that URL means
that round **succeeded** and the reboot is the problem, not the install.

Then remove the host's entry from `bootstrap_grub_mac_configs`, re-run the `grub-mac` tag,
and delete the leftover `grub.cfg-*` files by hand — that role renders configs but never
prunes them.

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

### It boots the interactive menu instead of installing

The MAC-pinned GRUB config is missing, or the firmware's `$net_default_mac` format has no
matching variant on disk.

### It reinstalls itself on every reboot

The boot order was never pinned to the disk after the install.

### The guest is up but on the wrong address

Its reservation is missing or duplicated. `opnsense_dhcp` skips a host whose MAC is empty
**silently**, so confirm the reservation exists on the core router rather than assuming the
play wrote it.
