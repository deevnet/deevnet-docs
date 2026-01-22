---
title: "PXE Role"
weight: 3
---

# PXE Role

## Purpose

The PXE boot infrastructure enables **fully automated, zero-touch provisioning** of bare-metal hosts. Hosts boot from the network, receive their OS installation automatically based on their MAC address, and require no human intervention.

Goals:
- **Zero-touch** — MAC-specific configs eliminate boot menus and manual selection
- **UEFI-native** — Modern UEFI boot with network-enabled GRUB
- **Decoupled services** — DHCP (Core Router) and TFTP (bootstrap node) are separate
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

---

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   PXE Client    │◄──DHCP──│   Core Router    │         │  Bootstrap Node │
│  (VM or bare)   │         │   (Kea DHCP)     │         │    (TFTP)       │
└────────┬────────┘         └──────────────────┘         └────────┬────────┘
         │                                                        │
         │                         TFTP                           │
         └───────────────────────────────────────────────────────►│
                            grubx64.efi                           │
                            grub.cfg-<MAC>                        │
                            vmlinuz, initrd.img                   │
```

| Component | Host | Implementation | Role |
|-----------|------|----------------|------|
| **DHCP** | Core Router (core-rt02) | Kea | Provides IP, next-server, boot-file-name |
| **TFTP** | Bootstrap node | in.tftpd (systemd socket) | Serves bootloader, configs, kernel/initrd |
| **Bootloader** | — | GRUB (grub2-mkimage) | Network-enabled UEFI bootloader |
| **Artifacts** | Bootstrap node | nginx | Kickstart files, install trees, squashfs |

> **Note:** The Core Router is currently OPNsense but the PXE infrastructure works with any router providing Kea DHCP with PXE options.

---

## DHCP Configuration (Core Router)

The Core Router's Kea DHCP provides two critical options for PXE:

| Option | Value | Purpose |
|--------|-------|---------|
| **next-server** | 192.168.10.95 | TFTP server IP (bootstrap node) |
| **boot-file-name** | grubx64.efi | UEFI bootloader filename |

### Subnet-Level Settings

Applied to all hosts on the subnet unless overridden:

```
Subnet: 192.168.10.0/23
Next Server: 192.168.10.95
Boot File Name: grubx64.efi
```

### Per-Host Reservations

**Per-host reservations override subnet settings.** Each PXE-bootable host must have:

| Field | Example | Notes |
|-------|---------|-------|
| MAC Address | BC:24:11:2E:26:4E | Hardware address |
| IP Address | 192.168.10.20 | Static reservation |
| Hostname | vyos-rt01 | DNS hostname |
| TFTP Server | 192.168.10.95 | Next-server for this host |
| Boot File | grubx64.efi | UEFI bootloader |

---

## TFTP Server (Bootstrap Node)

The bootstrap node runs `in.tftpd` via systemd socket activation:

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
├── grub.cfg-BC:24:11:2E:26:4E     # MAC-specific: vyos-rt01
├── grub.cfg-BC:24:11:F0:E4:68     # MAC-specific: provisioner-vm05
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

**Example: `/srv/tftp/grub.cfg-BC:24:11:2E:26:4E`** (vyos-rt01)

```
set timeout=0
set default=0

menuentry "VyOS Rolling" {
    linux /vyos/vmlinuz boot=live noautologin fetch=http://artifacts.dvntm.deevnet.net/netboot/vyos/filesystem.squashfs
    initrd /vyos/initrd.img
}
```

**Example: `/srv/tftp/grub.cfg-BC:24:11:F0:E4:68`** (provisioner-vm05)

```
set timeout=0
set default=0

menuentry "Fedora 43 Server" {
    linux /fedora/43/vmlinuz ip=dhcp rd.neednet=1 inst.repo=http://artifacts.dvntm.deevnet.net/fedora/43/mirror inst.ks=http://artifacts.dvntm.deevnet.net/kickstart/builder-node.ks
    initrd /fedora/43/initrd.img
}
```

Key points:
- **timeout=0** — No menu, boots immediately
- **default=0** — First (only) entry
- **Kernel options** — Point to artifact server for install media

---

## Adding a New PXE Host

### 1. Add DHCP Reservation (Core Router)

Via Core Router UI or API, create a host reservation:

```
MAC Address: <new-host-mac>
IP Address: <static-ip>
Hostname: <hostname>
TFTP Server Name: 192.168.10.95
Boot File Name: grubx64.efi
```

### 2. Add to Ansible Inventory

In `ansible-inventory-deevnet/dvntm/group_vars/bootstrap_nodes.yml`:

```yaml
bootstrap_grub_mac_configs:
  - hostname: new-host
    mac: "aa:bb:cc:dd:ee:ff"
    image_name: "Fedora 43 Server"
    dest_subdir: "fedora/43"
    boot_options: >-
      inst.repo=http://artifacts.dvntm.deevnet.net/fedora/43/mirror
      inst.ks=http://artifacts.dvntm.deevnet.net/kickstart/builder-node.ks
```

### 3. Apply Bootstrap Role

```bash
cd ~/dvnt/ansible-collection-deevnet.builder
make rebuild
ansible-playbook playbooks/site.yml --limit bootstrap_nodes
```

### 4. Reconfigure Kea

After adding DHCP reservation:

```bash
# Via Core Router API
curl -X POST "https://core-rt02/api/kea/service/reconfigure"
```

---

## Boot Sequence

1. **Power on** — Host starts UEFI PXE boot
2. **DHCP** — Core Router Kea provides IP + next-server (192.168.10.95) + boot-file (grubx64.efi)
3. **TFTP grubx64.efi** — Host downloads network-enabled GRUB
4. **TFTP grub.cfg** — GRUB fetches default config
5. **TFTP grub.cfg-MAC** — GRUB finds MAC-specific config (no menu)
6. **TFTP kernel/initrd** — GRUB downloads OS boot files
7. **HTTP install** — Installer fetches packages from artifact server
8. **Kickstart** — Automated installation completes

---

## Troubleshooting

### Check DHCP Options

On the PXE boot screen, verify:
- **Server IP**: Should be 192.168.10.95 (not 192.168.10.1)
- **Boot file**: Should be grubx64.efi

If wrong, check both subnet AND per-host reservation in Kea.

### Check TFTP Logs

```bash
# On bootstrap node
journalctl -u tftp.service -f
```

Look for:
- `RRQ from <ip> filename grubx64.efi` — Bootloader request
- `Client <ip> finished grubx64.efi` — Successful transfer
- `RRQ from <ip> filename /grub.cfg-<MAC>` — Config lookup

### Verify Files Exist

```bash
# On bootstrap node
ls -la /srv/tftp/grubx64.efi
ls -la /srv/tftp/grub.cfg-*
```

### Test TFTP Manually

```bash
tftp 192.168.10.95 -c get grubx64.efi /tmp/test.efi
ls -la /tmp/test.efi  # Should be ~1.2MB
```

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
2. **TFTP** (bootstrap node) serves GRUB and boot files
3. **MAC-specific configs** enable zero-touch automated installs
4. **Per-host reservations** override subnet defaults — update both when adding hosts
