---
title: "CHG-0074: A Take-Home Virtual Machine Image"
weight: -74
---

# CHG-0074: A Take-Home Virtual Machine Image

| | |
|---|---|
| **Date** | 2026-11-17 |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | **In progress** |
| **Window** | Unscheduled. Downloads across the core router are throttled; the image build and its proof run on the Builder |
| **Site** | mobile |
| **Systems** | `deevnet-kit`; the log bridge; the artifact server on the Builder; the take-home virtual machine image; the tenant downloads on `dv02obs001v01`; `deevnet-tenant-tdemo` |
| **Automation** | `deevnet-provisioning-api` (`cmd/deevnet-kit`), `deevnet-log-bridge`, `deevnet-image-factory` |
| **Risk** | Low. Nothing runs on Deevnet's hosts but the artifact server and the tenant downloads. Most likely to go wrong: a download across the core router, which is throttled |
| **Related changes** | [CHG-0072](/docs/changes/2026/0072-pi-metrics-and-alerting/), [CHG-0073](/docs/changes/2026/0073-pi-buckets/) (the Pi image it mirrors), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (tenant downloads) |
| **Related runbooks** | [Convert a Tenant to a Pi Image](/docs/runbook/tenant/tenant-to-pi-image/) |

---

## Summary

A tenant takes its backend home on a Raspberry Pi. This change builds the same backend as an
**amd64 virtual machine image** (qcow2) for Proxmox and KVM, the first version of
[Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/). It starts from
Debian 12's official `nocloud` image, as the Pi image starts from Raspberry Pi OS, and the same
configuration play makes it the backend. A VM has no boot partition to edit, so its first boot
asks on the console for the user, the sign-in and the host name, through a new
`deevnet-kit setup`.

## Goal

- One `make` target on the Builder builds the image from the Pi image's configuration play.
- The image's self-test passes every check, and `tdemo` moves across with its `kit.env`.
- The image is in the tenant downloads, with a section in the tenant guide.

## Scope

**In scope:**
- **amd64 inputs:** `deevnet-kit`, `deevnet-log-user` and the log bridge built for amd64; the
  upstream amd64 releases at the Pi's versions; silo from the amd64 image Deevnet runs, which is
  built from the same release.
- **`deevnet-kit setup`:** the console prompt, writing the settings the Pi reads from its boot
  partition.
- **The image:** Debian 12 bookworm, as on the Pi, built and published to `tenant/vm`.

**Out of scope:**
- The ISO, OVA, VHDX and the arm64 image for UTM: later versions of Take-Home Media.
- A run on the lab's hypervisors. The image is proven on the Builder under qemu.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A download hangs the core router | Network | Each download is throttled, and each file is fetched once and staged |
| The amd64 build differs from the Pi's | Supply | The same versions, pinned by sha256; the same play and self-test |
| The image carries the build's accounts or keys | The image | The play's existing removal of the automation user and the SSH host keys |

## Prerequisites

- [x] The take-home Pi image with metrics, alerting and buckets (CHG-0072, CHG-0073)
- [x] The vendor claims checked (Step 1)

## Procedure

### Step 1: Check the vendor claims

- Debian 12's `nocloud` image has no cloud-init, and its root file system can be grown in place.
- The upstream amd64 releases at the Pi's versions, and their published checksums.
- The silo binary in Deevnet's image is static.

**Done 2026-11-17.** Checked against the build itself, Debian `20261117-2665`, with its published
SHA512:

- **It has no cloud-init**, as its manifest's package list shows. It also has no `openssh-server`,
  `cloud-guest-utils` or `avahi-daemon`; the image installs them.
- **Root signs in with no password** (an empty field in `/etc/shadow`). The image locks root, and
  its build fails if root is not locked.
- **It configures no network.** `systemd-networkd` is enabled, but no `.network` file matches an
  Ethernet adapter. The image adds DHCP on any Ethernet adapter, with the MAC as the client ID.
- **The root is partition 1, ext4, on a 3 GiB GPT disk**, beside BIOS boot and EFI partitions,
  so it boots on either firmware. It grows with `growpart` and `resize2fs`.
- **Its machine ID is empty**, so each VM makes its own.
- The kernel console is `tty0` and `ttyS0`; the console prompt runs on `tty1`.
- **The amd64 releases exist at every version the Pi pins**, each with a published checksum:
  VictoriaLogs v1.52.0, vmutils and the cluster v1.156.0, Alertmanager 0.35.0, ntfy 2.38.0 and
  Grafana 13.2.2.
- **The silo binary in Deevnet's amd64 image is static** (`file`: statically linked), made by the
  same build stage as the arm64 one, so it is staged from that image and needs no build.

### Step 2: The amd64 inputs

Build and stage `deevnet-kit`, `deevnet-log-user` and the log bridge for amd64. Stage the
upstream releases and the Debian image, throttled.

**Done 2026-11-17.** On the artifact server, beside the arm64 builds:
- `deevnet-kit` and `deevnet-log-user` v0.27.0, by `make stage-vm`;
- the log bridge `v0.1.1-1-g20abb75`, built from the commit the Pi pins;
- silo `RELEASE.2026-11-12T00-00-00Z`, taken from the amd64 image Deevnet runs, with its sha256;
- the upstream releases and Debian's image, 1.15 GB fetched once at 1.5 MB/s, with 0 of 374 pings
  to the core router missed. Each was checked against its published checksum.

`make vm-backend-stage-upstream` then found every file already staged with its checksum, and
fetched nothing.

### Step 3: `deevnet-kit setup`

The console prompt, in a `deevnet-kit` release.

**Done 2026-11-17:** `deevnet-kit` v0.27.0 (API #81, release #82). The first boot under qemu found
that SSH started before setup wrote its key-only drop-in, so passwords stayed on until the next
boot. Setup now reloads SSH; that fix is in the release.

### Step 4: The image

A `make` target in `deevnet-image-factory` that builds the qcow2.

**Done 2026-11-17:** `make vm-backend` (image factory #46). The Pi's play takes `medium=vm`, and the
Makefile's inputs and staging steps take the architecture, so both media fetch through one recipe.
The Pi's inputs step was re-run after that change, and passed every check. The image is 1.46 GB,
built from scratch with kit v0.27.0.

### Step 5: Prove it on the Builder

Under qemu: answer the prompt, run the self-test, and move `tdemo` across with its `kit.env`.

**Done 2026-11-17**, under qemu/KVM on the Builder, on a 24 GB overlay with its ports forwarded to
localhost:
- **The console prompt works.** It asks once, with the password hidden, and the screen starts
  clear of the boot messages.
- **Root grew** to fill the 24 GB disk, the VM made its own machine ID, and the login is in `sudo`.
- **SSH** takes keys only when a key was given (`sshd -T`: `passwordauthentication no`), and
  passwords otherwise.
- **The self-test passed all 27 checks** on first boot, in three boots: two with test builds of the
  kit and one with the released image, which took every default (tenant `pi`, host `pi-kit`).
- **`tdemo` moved across.** `backend` and `pico-1` were recreated with their Deevnet passwords. The
  app received `pico-1`'s telemetry with only the exported `kit.env`, and `pico-1`'s log line read
  back through Grafana with the tenant login. TLS verified for `tdemo-vm.local` on 8883, 8427, 3000
  and 443 from outside the VM.

### Step 6: Publish

The image under `tenant/vm` in the tenant downloads, with its sha256, and a section in the
tenant guide.

## Verification

On the Builder, under qemu:
- The first boot asks for the user, the sign-in and the host name, and then makes the CA and the
  secrets.
- `deevnet-kit selftest` passes every check.
- With `tdemo`'s `kit.env`, a test client publishes, and its log shows in Grafana.
- The published image's sha256 matches the one built.

## Undo

Remove the image from the tenant downloads. The staged amd64 inputs are additive.

## To close

**This change closes when every item below is done.**

- [x] Step 1: the vendor claims checked and recorded
- [x] Step 2: the amd64 inputs built and staged
- [x] Step 3: `deevnet-kit setup` released
- [x] Step 4: the image builds
- [x] Step 5: proven on the Builder
- [ ] Step 6: published, with the guide section
