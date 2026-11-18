---
title: "Take-Home Media"
bookCollapseSection: true
weight: 6
value: [works-anywhere]
waypoints:
  - title: "Deevnet's take-home tools built for amd64 computers: deevnet-kit, the log bridge and the silo bucket store"
    status: done
    date: "2026-11-17"
  - title: "A take-home virtual machine image of the tenant backend, built from the same configuration as the Pi image"
    status: done
    date: "2026-11-17"
  - title: "The take-home virtual machine asks its owner for a user, a sign-in and a host name on its first boot"
    value: [works-anywhere, secure-by-default]
    status: done
    date: "2026-11-17"
  - title: "The take-home virtual machine passes its full self-test and takes a tenant across with one file"
    status: done
    date: "2026-11-17"
  - title: "Take-home media v1 done: a virtual machine image of the tenant backend for Proxmox and KVM, in the tenant downloads"
    milestone: true
    status: done
    date: "2026-11-17"
  - title: "An ISO that installs the take-home tenant backend on an owner's own hardware"
    status: planned
  - title: "The take-home virtual machine for VirtualBox, Hyper-V and UTM on Apple Silicon"
    status: planned
---

# Take-Home Media

A tenant takes its backend home on a Raspberry Pi today, flashed from the `pi-backend` image in the
tenant downloads. This item adds the same backend on two more media: a virtual machine image, then
an ISO that installs it on an owner's own hardware. The app contract, deevnet-kit and the self-test
stay the Pi's on every medium
([proposal](/docs/architecture/proposals/take-home-vm-and-iso/)).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}

**Project plan:** [Take-Home Media](/docs/roadmap/infrastructure/tenant-services/take-home-media/plan/)
