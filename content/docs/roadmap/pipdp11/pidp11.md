---
title: "PiDP-11"
aliases:
  - /docs/roadmap/raspberry-pi/pidp11/
weight: 1
tasks_completed: 1
tasks_in_progress: 1
tasks_planned: 8
---

# PiDP-11 Project

Hardware adoption of the PiDP-11 kit — a PDP-11 replica using simh emulation on Raspberry Pi.

Part of `deevnet-image-factory`.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Build a functional PDP-11 replica by assembling the PiDP-11 kit and running simh emulation, capable of running period-accurate operating systems with an authentic front panel experience.

**In Scope**
- PiDP-11 kit assembly and testing
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

## Kit Assembly ⏳

PiDP-11 kit build and hardware verification.

- ⏳ Pretest components before soldering
- ⏳ Assemble kit per instructions
- ⏳ Verify front panel LED/switch operation

---

## simh Emulation 🔄

PDP-11 emulation running on Raspberry Pi.

- ✅ Base Pi image with ansible support
- 🔄 simh installation and configuration
- ⏳ Multiple OS options (RT-11, RSX-11, 2.11BSD)

---

## Documentation ⏳

- ⏳ Build documentation
- ⏳ Usage guide
