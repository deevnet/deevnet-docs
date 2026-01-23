---
title: "Pi Stratum 1"
weight: 3
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 9
---

# Pi Stratum 1 NTP Server

Raspberry Pi Zero-based Stratum 1 NTP server with GPS time source.

Part of `deevnet-image-factory`.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Deploy a local Stratum 1 NTP server using GPS as the time source, providing accurate time synchronization for all substrate hosts independent of internet connectivity.

**In Scope**
- GPS-disciplined NTP server on Pi Zero
- Serve time to substrate hosts
- Air-gap capable (no internet required)
- Baked image via deevnet-image-factory

**Out of Scope**
- Public NTP service
- Redundant time sources

---

## Requirements ⏳

- ⏳ Define time accuracy requirements
- ⏳ Define GPS antenna placement constraints
- ⏳ Define telemetry and alerting requirements

---

## Hardware ⏳

- ⏳ Pi Zero W/2W selection
- ⏳ GPS HAT/module selection
- ⏳ Hardware acquisition

---

## Image Build ⏳

- ⏳ Base Pi Zero image
- ⏳ GPS daemon (gpsd) configuration
- ⏳ NTP/Chrony configuration for Stratum 1
- ⏳ Telemetry and alerting configuration
- ⏳ Test scripts for time accuracy validation

---

## Deployment ⏳

- ⏳ Network position and VLAN assignment
- ⏳ Client configuration to use Stratum 1
- ⏳ Build documentation
