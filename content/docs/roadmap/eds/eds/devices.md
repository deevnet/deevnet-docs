---
title: "Devices and Firmware"
weight: 5
milestones:
  - title: "A power beacon on the turntable: when it connects, the turntable is on (EdS ADR-0023)"
    group: "Devices"
    status: done
    date: "2026-10-12"
  - title: "EdS device secrets kept only in ESP32 flash storage, and the MQTT broker's CA loaded (EdS ADR-0004)"
    group: "Devices"
    status: done
    date: "2026-10-10"
  - title: "EdS device events sent over MQTT into the central log store (EdS ADR-0005, ADR-0017)"
    group: "Devices"
    status: done
    date: "2026-10-11"
  - title: "Each EdS device reports its presence every thirty seconds (EdS ADR-0034)"
    group: "Devices"
    status: done
    date: "2026-10-16"
  - title: "EdS's ESP32 devices verify the MQTT broker's certificate up to the Deevnet root (EdS CHG-0042)"
    group: "Devices"
    status: done
    date: "2026-10-26"
  - title: "EdS firmware updated over the air through the MQTT broker, rolled back if the new build cannot reach it (EdS ADR-0035)"
    group: "Updates"
    status: done
    date: "2026-10-17"
  - title: "EdS firmware updates at home, served from the Pi that runs its back end (EdS CHG-0028)"
    group: "Updates"
    status: planned
  - title: "EdS device setup writes the settings for two locations, the mobile site and home (EdS ADR-0049)"
    group: "Two sites"
    status: done
    date: "2026-10-26"
  - title: "EdS's turntable beacon, touch screen and LP stand each hold settings for a second location (EdS CHG-0042)"
    group: "Two sites"
    status: planned
  - title: "EdS firmware switches between its two locations on a message (EdS ADR-0049)"
    group: "Two sites"
    status: planned
---
# Devices and Firmware

The stand, the cover screen, the power beacon and the reSpeaker: ESP32s on the broker, updated through it.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---
## Project Vision & Scope

Devices that fail soft, say where they are, take updates over the air and can be moved between sites without a cable.

**In Scope**
- Firmware, provisioning, presence, updates
- Holding two sites

**Out of Scope**
- Device certificates: Tenant PKI, under Tenant Services Tooling

---

## Devices ✅

{{< milestones group="Devices" >}}

---

## Updates 🔄

{{< milestones group="Updates" >}}

---

## Two sites 🔄

{{< milestones group="Two sites" >}}
