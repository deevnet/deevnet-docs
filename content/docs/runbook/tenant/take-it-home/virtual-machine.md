---
title: "On a Virtual Machine"
weight: 3
---

# On a Virtual Machine

**The backend comes as a virtual machine for the hypervisor you already run, and its first boot
asks for your settings on the console.** It runs the same services, `deevnet-kit` and self-test as
every other medium. All the images are in the
[tenant downloads](/docs/runbook/tenant/getting-started/before-you-start/#tenant-downloads) `vm/`,
each with its `.sha256`: check the one you take before you import it.

| Hypervisor | File | Machine |
|---|---|---|
| [Proxmox or KVM](#on-proxmox-or-kvm) | `debian-bookworm-mobile-vm-backend.qcow2` | amd64 |
| [VirtualBox](#on-virtualbox) | `debian-bookworm-mobile-vm-backend.ova` | amd64, BIOS |
| [Hyper-V](#on-hyper-v) | `debian-bookworm-mobile-vm-backend.vhdx.zip` | amd64, Generation 2 |
| [UTM, on a Mac with Apple Silicon](#on-utm) | `debian-bookworm-mobile-vm-backend-arm64.qcow2` | arm64, UEFI |

**Every one needs a bridged network.** Your devices connect to the backend, so it needs its own
address on your network; behind the hypervisor's NAT they cannot reach it. Give it 2 CPUs and 2 GB
of memory. Its disk is 16 GB: make it bigger whenever you like, and the file system grows to fill
it on each boot.

## On Proxmox or KVM

**On Proxmox, import the qcow2 as the VM's disk.** With VM ID 900, storage `local-lvm` and bridge
`vmbr0`:

```bash
qm create 900 --name bench1 --memory 2048 --cores 2 \
  --net0 virtio,bridge=vmbr0 --scsihw virtio-scsi-single \
  --agent enabled=1 --ostype l26
qm importdisk 900 debian-bookworm-mobile-vm-backend.qcow2 local-lvm
qm set 900 --scsi0 local-lvm:vm-900-disk-0 --boot order=scsi0
```

On plain KVM, use the qcow2 as the disk of a new machine on a bridge. Then start it and
[answer the console](#first-boot).

## On VirtualBox

**For VirtualBox, the backend comes as an OVA, with its settings made.**

1. **Import it**: File, Import Appliance, then choose the file. It brings 2 CPUs, 2 GB of memory,
   the disk, and a network adapter set to **Bridged Adapter**. From a terminal,
   `VBoxManage import debian-bookworm-mobile-vm-backend.ova`.
2. **Choose the bridge**: open the VM's Settings, Network, and under Name choose the network
   interface your computer is on, Wi-Fi or Ethernet.

It starts by BIOS, VirtualBox's default. Then start it and [answer the console](#first-boot).

## On Hyper-V

**For Hyper-V, on Windows 10 or 11 Pro and Windows Server, the backend comes as a VHDX for a
Generation 2 machine.**

1. **Extract the `.vhdx`** from the zip, where the VM's disk will live.
2. **Make an external switch**, once, so the VM has its own address on your network: in Hyper-V
   Manager, Virtual Switch Manager, an **External** switch on the network interface your computer
   is on. The default switch is NAT, and your devices cannot reach the VM behind it.
3. **Make the VM**, Generation 2, with the VHDX as its disk and the external switch as its network.
   **Secure Boot can stay on, with the "Microsoft UEFI Certificate Authority" template.** The
   default template, "Microsoft Windows", refuses Debian's signed boot loader. In PowerShell as
   administrator, with a switch named `External`:

   ```powershell
   New-VM -Name bench1 -Generation 2 -MemoryStartupBytes 2GB `
     -VHDPath C:\VMs\debian-bookworm-mobile-vm-backend.vhdx -SwitchName External
   Set-VMProcessor bench1 -Count 2
   Set-VMFirmware bench1 -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority
   Start-VM bench1
   ```

Then connect to its console and [answer it](#first-boot).

## On UTM

**On a Mac with Apple Silicon, the backend comes as an arm64 image for UTM's QEMU backend.**

1. **Check it** in Terminal: `shasum -a 256 -c debian-bookworm-mobile-vm-backend-arm64.qcow2.sha256`.
2. **Make the VM** with the "+" button: **Virtualize**, then **Linux**, 2 GB of memory and 2 CPU
   cores. **Leave "Use Apple Virtualization" off**: the image is made for the QEMU backend. Give it
   no installer ISO; the disk you import boots by itself.
3. **Before you start it, open its settings.** Under Drives, choose **New…** and import the qcow2;
   UTM copies it into the VM. Delete the empty drive the wizard made (right-click it, Delete), so
   the imported disk is the only one.
4. **Set the network to Bridged**, and under Bridged Interface choose the interface your Mac is
   on, Wi-Fi or Ethernet. UTM's default, Shared Network, puts the VM behind your Mac, where your
   devices cannot reach it. UTM calls bridging "for advanced users" and notes that "bridging with
   an Wifi interface may require additional configuration".

It starts by UEFI. Then start it and [answer the console](#first-boot). If the window goes dark
after the boot menu, give it a virtio display (Display, Emulated Display Card): the console needs
Linux's virtio-gpu driver.

## First boot

**A VM has no boot partition to edit, so its first boot asks on the console, once, for what a Pi's
owner writes on the card:**

| Asked | Answer | Left empty |
|---|---|---|
| Tenant, tenant index | your Deevnet tenant's name and index (`terraform output`) | `pi`, 1 |
| Host name | the VM becomes `<hostname>.local`, and its certificate names it | `<tenant>-kit` |
| Your login name | yours to choose; the image has no user of its own | |
| Password | for the console, `sudo` and, without a key, SSH | |
| SSH public key | one line, such as your `~/.ssh/id_ed25519.pub`. With a key, SSH takes keys only | password sign-in |

The console's keyboard is a US layout. Then `deevnet-kit` makes the backend, as on every medium,
and you sign in with `ssh you@<hostname>.local`. A fixed address for the VM on your router keeps
its certificate right.

## What is different on a VM

- **Your app's container is built for the VM's architecture:** `podman build --platform
  linux/amd64`, or on UTM `--platform linux/arm64`.
- **The VM keeps the hypervisor's clock.**
- **It has no Wi-Fi of its own:** the bridged adapter is its network.

{{< hint info >}}
**Proven in qemu on the Builder, 2026-11-17 and 2026-11-18.** Each image booted in the firmware
its hypervisor gives it and passed every self-test check. Not yet tried on a real VirtualBox,
Hyper-V or UTM host, or bridged on Wi-Fi.
{{< /hint >}}

Next: [Check the backend](/docs/runbook/tenant/take-it-home/check-the-backend/).
