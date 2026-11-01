---
title: "Devices and Firmware"
weight: 5
tasks_completed: 7
tasks_in_progress: 0
tasks_planned: 3
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

- ✅ The power beacon: its connection is the turntable switched on (EdS ADR-0023)
- ✅ Secrets in NVS only; the broker's CA provisioned (EdS ADR-0004)
- ✅ Events over the bus into the log store (EdS ADR-0005, ADR-0017)
- ✅ Presence said every thirty seconds (EdS ADR-0034)
- ✅ ESP32s verify a broker through the Tenant Service CA to the Deevnet Root (EdS CHG-0042)

---

## Updates 🔄

- ✅ Over the air through the broker, undone if the build cannot reach it (EdS ADR-0035)
- ⏳ Updates at home, from the backend Pi (EdS CHG-0028)

---

## Two sites 🔄

- ✅ Provisioning writes both sites (EdS ADR-0049)
- ⏳ The second site on the beacon, the screen and the stand (EdS CHG-0042)
- ⏳ Firmware that switches between them by a message (EdS ADR-0049)
