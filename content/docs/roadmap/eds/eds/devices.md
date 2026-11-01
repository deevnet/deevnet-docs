---
title: "Devices and Firmware"
weight: 5
milestones:
  - title: "The power beacon: its connection is the turntable switched on (EdS ADR-0023)"
    group: "Devices"
    status: done
    date: "2026-10-12"
  - title: "Secrets in NVS only; the broker's CA provisioned (EdS ADR-0004)"
    group: "Devices"
    status: done
    date: "2026-10-10"
  - title: "Events over the bus into the log store (EdS ADR-0005, ADR-0017)"
    group: "Devices"
    status: done
    date: "2026-10-11"
  - title: "Presence said every thirty seconds (EdS ADR-0034)"
    group: "Devices"
    status: done
    date: "2026-10-16"
  - title: "ESP32s verify a broker through the Tenant Service CA to the Deevnet Root (EdS CHG-0042)"
    group: "Devices"
    status: done
    date: "2026-10-26"
  - title: "Over the air through the broker, undone if the build cannot reach it (EdS ADR-0035)"
    group: "Updates"
    status: done
    date: "2026-10-17"
  - title: "Updates at home, from the backend Pi (EdS CHG-0028)"
    group: "Updates"
    status: planned
  - title: "Provisioning writes both sites (EdS ADR-0049)"
    group: "Two sites"
    status: done
    date: "2026-10-26"
  - title: "The second site on the beacon, the screen and the stand (EdS CHG-0042)"
    group: "Two sites"
    status: planned
  - title: "Firmware that switches between them by a message (EdS ADR-0049)"
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
