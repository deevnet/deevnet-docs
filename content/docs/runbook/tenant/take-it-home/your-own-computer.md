---
title: "On a Computer of Your Own"
weight: 4
---

# On a Computer of Your Own

**The backend installs on a spare amd64 computer from a USB stick.** The stick writes the virtual
machine's system to the computer's disk, so the computer then runs exactly what the
[VM](/docs/runbook/tenant/take-it-home/virtual-machine/) runs. It erases the disk you choose. The
installed system has no Wi-Fi: connect the computer by cable.

## Install it

1. **Get the installer.** At the site it is in the
   [tenant downloads](/docs/runbook/tenant/getting-started/before-you-start/#tenant-downloads)
   `iso/`: `debian-bookworm-mobile-backend-installer.iso`, with its `.sha256`. Check it.
2. **Write it to a USB stick** of 2 GB or more, as a raw image, which erases the stick:
   balenaEtcher or Raspberry Pi Imager ("Use custom"), or on Linux or macOS
   `sudo dd if=debian-bookworm-mobile-backend-installer.iso of=/dev/<stick> bs=4M`. If Rufus asks
   on Windows, choose **DD image** mode: the installer finds its stick by the stick's name, which
   Rufus's ISO mode shortens.
3. **Start the computer from the stick,** with its network cable plugged in. Most computers show a
   boot menu on a key at power-on, often F12, F11 or Esc. **Secure Boot can stay on**: the stick
   and the installed system start through Debian's signed boot loader and kernel. If the computer
   refuses to start the stick, turn Secure Boot off in its firmware settings.
4. **Choose the disk.** The installer lists the computer's disks of 16 GB or more, never the stick
   itself. Type the name of the one to install to, such as `sda` or `nvme0n1`, then type it again
   to confirm. **Everything on that disk is erased.** The installer writes the system, reads it
   back to check it, and asks you to remove the stick and press Enter.

## First boot

**The computer's first boot asks the same questions as the VM's**, on its own screen
([the VM's first boot](/docs/runbook/tenant/take-it-home/virtual-machine/#first-boot)): your
tenant, the host name, and your login. The root file system grows to fill the disk, and you sign in
with `ssh you@<hostname>.local`.

## What is different on your own computer

- **Your app's container is built for amd64:** `podman build --platform linux/amd64`.
- **The computer keeps its own clock.**
- **It is wired only.** Wi-Fi on the installed system is not there yet.

{{< hint info >}}
**Proven in qemu on the Builder, 2026-11-17**, under BIOS, UEFI, and UEFI with Secure Boot: the
installer refused its own stick and a wrong confirmation, and the installed system passed every
self-test check. Not yet tried on a real computer.
{{< /hint >}}

Next: [Check the backend](/docs/runbook/tenant/take-it-home/check-the-backend/).
