---
title: "Image Factories"
weight: 6
---

# Image Factories

Two repositories that build what the site installs from. Both run on the Builder, and stage their
output on the artifact server.

## `deevnet-image-factory`: OS images

Packer and Ansible builds of:

| Image | Target |
|---|---|
| Fedora VM templates | Built straight onto each hypervisor: `make proxmox-fedora-pve1`, `make proxmox-fedora-pve2` |
| Raspberry Pi images | `make pi-sdr`, `make pi-pidp11`, and `make pi-backend` (the take-home tenant backend, with [deevnet-kit](/docs/platforms/deevnet-software/deevnet-kit/)) |
| Proxmox VE install ISO and PXE artifacts | `make proxmox-pve-iso-ext4` and related targets. **Unfinished**: neither hypervisor has been installed from it ([Builder roadmap](/docs/roadmap/infrastructure/mobile/builder/)) |

Its `scripts/pve-creds` fetches a hypervisor's Proxmox token per run, from OpenBao or the inventory
vault, and never writes it to disk; the tenant fabric's Terraform uses it too
([Build-Time Secrets](/docs/runbook/substrate/building-recovery/build-secrets/)).

## `deevnet-container-image-factory`: service images from source

Builds container images, from source, for third-party software whose source may be used but whose
binaries may not be redistributed. Today that is only VerneMQ, the site's
[MQTT broker](/docs/changes/2026/0015-vernemq-broker/), whose released binaries are under an EULA
while its source is Apache-2.0. `make image IMAGE=vernemq` builds it and `make stage IMAGE=vernemq`
puts it on the artifact server, where the `vernemq` role picks it up.
