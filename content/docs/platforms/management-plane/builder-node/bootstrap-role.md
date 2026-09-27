---
title: "Bootstrap Role"
weight: 3
aliases:
  - /docs/platforms/management-plane/bootstrap-node/pxe-role/
---

# Bootstrap Role

The `bootstrap` role in `deevnet.builder` makes the Builder the thing new hosts boot from. It works in
two modes ([Builder → Authority Transition](/docs/architecture/builder/#authority-transition)):

| Mode | The Builder provides | Switched by |
|---|---|---|
| **Core-authoritative** (normal) | PXE boot files over TFTP (`in.tftpd`); the core router answers DNS and DHCP | `make core-auth` |
| **Bootstrap-authoritative** | DNS, DHCP and TFTP from dnsmasq, and the site's gateway, with records and reservations from inventory | `make bootstrap-auth` |

The rest of this page is the PXE side, which is the same in both modes. How to switch is
[Authority Transition](/docs/runbook/substrate/building-recovery/authority-transition/).

---

## Purpose

The PXE boot infrastructure enables **fully automated, zero-touch provisioning** of bare-metal hosts. Hosts boot from the network, receive their OS installation automatically based on their MAC address, and require no human intervention.

Goals:
- **Zero-touch** — MAC-specific configs eliminate boot menus and manual selection
- **UEFI-native** — Modern UEFI boot with network-enabled GRUB
- **Decoupled services** — DHCP (Core Router) and TFTP (the Builder) are separate
- **Air-gap capable** — All boot artifacts served from local infrastructure

---

## Use Cases

### Primary: Bare-Metal Provisioning

PXE boot is the standard method for provisioning bare-metal hosts:
- Proxmox hypervisors
- Physical workstations and admin nodes
- Network appliances (where supported)

### Secondary: VM Testing

VMs can PXE boot to validate new OS configurations before bare-metal deployment:
- Test kickstart changes without risking physical hardware
- Validate netboot image updates (kernel, initrd)
- Debug boot issues in a controlled environment

Once validated on VMs, the same MAC-specific config works unchanged on bare metal.

#### UEFI VM clients require a VirtIO RNG device

A Proxmox VM with `bios: ovmf` **cannot PXE boot without an entropy source**. This is a documented Proxmox 8.4 known issue — *"PXE boot on VM with OVMF requires VirtIO RNG"* ([Roadmap](https://pve.proxmox.com/wiki/Roadmap)) — and it arrived with `pve-edk2-firmware 4.2025.02` in PVE 8.3.5.

EDK II's fix for CVE-2023-45237 makes the UEFI network stack depend on `EFI_RNG_PROTOCOL`. With no entropy source the firmware **disables network boot entirely**, so it never creates a network boot entry and the guest emits **zero DHCP packets**:

```
BdsDxe: failed to load Boot0001 "UEFI QEMU QEMU HARDDISK " ... Not Found
BdsDxe: No bootable option or device was found.
```

Add the device when creating the VM:

```
rng0: source=/dev/urandom
```

Two things this failure is *not*, both verified on 2026-09-04 by rebuilding the VM from scratch each time and capturing on the segment:

- **Not the NIC model.** `virtio` and `e1000` fail identically without entropy and both work with it. Keep `virtio`, to match what `deevnet.mgmt` `roles/proxmox_vm` uses for every other VM.
- **Not stale firmware NVRAM.** A brand-new `efidisk0` behaves the same.

The alternative entropy source is a CPU exposing RDRAND (`cpu: host`, or a named model). VirtIO RNG is preferred: it is migration-safe. Note the PVE 8 default `kvm64` has no RDRAND, so a VM with neither setting has no entropy at all.

Bare-metal clients are unaffected — real firmware has its own entropy sources.

---

## Architecture

{{< mermaid >}}
sequenceDiagram
    participant Client as PXE Client<br>(VM or bare)
    participant Router as Core Router<br>(Kea DHCP)
    participant Boot as Builder<br>(TFTP)

    Client->>Router: DHCP Request
    Router-->>Client: IP + next-server + boot-file
    Client->>Boot: TFTP: grubx64.efi
    Client->>Boot: TFTP: grub.cfg-MAC
    Client->>Boot: TFTP: vmlinuz, initrd.img
{{< /mermaid >}}

| Component | Host | Implementation | Role |
|-----------|------|----------------|------|
| **DHCP** | Core Router (dv02cor002p01) | Kea | Provides IP, next-server, boot-file-name |
| **TFTP** | Builder | in.tftpd (systemd socket) | Serves bootloader, configs, kernel/initrd |
| **Bootloader** | — | GRUB (grub2-mkimage) | Network-enabled UEFI bootloader |
| **Artifacts** | Builder | nginx | Kickstart files, install trees, squashfs |

> **Note:** The Core Router is currently OPNsense but the PXE infrastructure works with any router providing Kea DHCP with PXE options.

---

## DHCP Configuration (Core Router)

The Core Router's Kea DHCP provides two critical options for PXE:

| Option | Value | Purpose |
|--------|-------|---------|
| **next-server** | 10.20.99.95 | TFTP server IP (Builder) |
| **boot-file-name** | grubx64.efi | UEFI bootloader filename |

### Subnet-Level Settings

```
Subnet: 10.20.99.0/24
Next Server: 10.20.99.95
```

**`next_server` must be set on the subnet, and no role manages it.** If it is empty, Kea advertises
its own address in `siaddr`, and UEFI firmware reads `siaddr` rather than DHCP option 66, so the
client tries to TFTP from the router.

### Per-Host Reservations

Reservations are generated from each host's `pxe_boot` block in inventory:

| Field | Example | Notes |
|-------|---------|-------|
| MAC Address | 02:DE:20:00:00:CB | Hardware address |
| IP Address | 10.20.99.96 | Static reservation |
| Hostname | dv02bld002v01 | DNS hostname |
| TFTP Server | 10.20.99.95 | Option 66 (`tftp_server_name`) |
| Boot File | grubx64.efi | UEFI bootloader |

A reservation carries option 66 but **no `next_server` field**, so it does not substitute for the
subnet setting above.

---

## TFTP Server (Builder)

The Builder runs `in.tftpd` via systemd socket activation:

```
Service: tftp.socket / tftp.service
Root: /srv/tftp
Port: 69/udp
```

### Directory Structure

```
/srv/tftp/
├── grubx64.efi                    # Network-enabled GRUB (built by grub2-mkimage)
├── grub.cfg                       # Default menu (fallback)
├── grub.cfg-02:DE:20:00:00:CB     # MAC-specific: dv02bld002v01
├── grub.cfg-02:de:20:00:00:cb     # ...and the lower-case variant
├── grub.cfg-02-DE-20-00-00-CB     # ...and both again, hyphen-separated
├── grub.cfg-02-de-20-00-00-cb     #    (firmware differs on which it asks for)
├── grub/
│   ├── grub.cfg                   # Alternate location
│   └── grub.cfg-*                 # MAC-specific configs
├── pxelinux.0                     # BIOS bootloader (legacy)
├── pxelinux.cfg/default           # BIOS menu (legacy)
├── fedora/43/
│   ├── vmlinuz                    # Fedora kernel
│   └── initrd.img                 # Fedora initramfs
└── vyos/
    ├── vmlinuz                    # VyOS kernel
    └── initrd.img                 # VyOS initramfs
```

---

## Network-Enabled GRUB

The bootloader is built with `grub2-mkimage` including network modules:

```bash
grub2-mkimage \
  -O x86_64-efi \
  -o /srv/tftp/grubx64.efi \
  -p "(tftp)/grub" \
  -d /usr/lib/grub/x86_64-efi \
  efinet tftp http net normal linux boot configfile \
  part_gpt part_msdos fat ext2 iso9660 \
  gzio all_video gfxterm
```

| Module | Purpose |
|--------|---------|
| efinet | EFI network interface |
| tftp | TFTP protocol support |
| http | HTTP protocol (for larger files) |
| net | Core networking |
| linux | Linux kernel loading |
| configfile | Load grub.cfg |

---

## MAC-Specific Boot Configs

Each host has a MAC-specific GRUB config that boots immediately without a menu:

**Example: `/srv/tftp/grub.cfg-02:DE:20:00:00:CB`** (dv02bld002v01)

```
# GRUB2 MAC-specific Boot Configuration
# Managed by Ansible - DO NOT EDIT MANUALLY
# Host: dv02bld002v01
# MAC: 02:de:20:00:00:cb

set default=0
set timeout=0

menuentry "Fedora 44 Server" {
    linux /fedora/44/vmlinuz \
        ip=dhcp \
        rd.neednet=1 \
        inst.repo=http://artifacts.mobile.deevnet.net/fedora/44/mirror inst.stage2=http://artifacts.mobile.deevnet.net/fedora/44/mirror inst.ks=http://artifacts.mobile.deevnet.net/kickstart/builder-node-44.ks
    initrd /fedora/44/initrd.img
}
```

Key points:
- **timeout=0** — No menu, boots immediately
- **default=0** — First (only) entry
- **Kernel options** — Point to artifact server for install media

---

## Adding a New PXE Host

To PXE-build a new host, see [Build a Management-Plane VM → Approach B](/docs/runbook/substrate/building-recovery/build-management-vm/#approach-b--pxe-netboot).

---

## Boot Sequence

1. **Power on** — Host starts UEFI PXE boot
2. **DHCP** — Core Router Kea provides IP + next-server (10.20.99.95) + boot-file (grubx64.efi)
3. **TFTP grubx64.efi** — Host downloads network-enabled GRUB
4. **TFTP grub.cfg** — GRUB fetches default config
5. **TFTP grub.cfg-MAC** — GRUB finds MAC-specific config (no menu)
6. **TFTP kernel/initrd** — GRUB downloads OS boot files
7. **HTTP install** — Installer fetches packages from artifact server
8. **Kickstart** — Automated installation completes

---

## Troubleshooting

See [Build a Management-Plane VM → Troubleshooting](/docs/runbook/substrate/building-recovery/build-management-vm/#troubleshooting).

---

## Ansible Configuration

The PXE infrastructure is managed by the `bootstrap` role in `deevnet.builder`:

| Variable | Default | Description |
|----------|---------|-------------|
| `bootstrap_uefi_bootloader` | "grub" | Bootloader: "grub", "ipxe", or "grub-local" |
| `bootstrap_tftp_root` | /srv/tftp | TFTP server root directory |
| `bootstrap_grub_timeout` | 30 | Menu timeout (seconds) for default config |
| `bootstrap_netboot_images` | [] | OS images for boot menu |
| `bootstrap_grub_mac_configs` | [] | MAC-specific auto-boot entries |

---

## Summary

1. **DHCP** (Core Router Kea) provides next-server and boot-file-name
2. **TFTP** (Builder) serves GRUB and boot files
3. **MAC-specific configs** enable zero-touch automated installs
4. **Subnet `next_server`** is required; per-host reservations do not replace it
