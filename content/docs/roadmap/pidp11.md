---
title: "PiDP-11"
weight: 3
tasks_completed: 1
tasks_in_progress: 1
tasks_planned: 4
---

# PiDP-11 Project

PDP-11 replica using simh emulation on Raspberry Pi.

Part of `deevnet-image-factory`.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Scope

Build a functional PDP-11 replica using the PiDP-11 kit with simh emulation, capable of running period-accurate operating systems.

**In Scope**
- simh PDP-11 emulation on Raspberry Pi
- Front panel LED/switch integration
- Multiple OS support (RT-11, RSX-11, 2.11BSD)
- Baked image via deevnet-image-factory

**Out of Scope**
- Network connectivity for the emulated PDP-11
- Integration with modern systems

---

## Requirements ⏳

- ⏳ Define default OS configuration
- ⏳ Define front panel behavior mapping

---

## simh Emulation 🔄

PDP-11 emulation running on Raspberry Pi.

- ✅ Base Pi image with ansible support
- 🔄 simh installation and configuration
- ⏳ Multiple OS options (RT-11, RSX-11, 2.11BSD)
- ⏳ Build documentation
