---
title: "Stratum 1 NTP: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/stratum1/
  - /projects/stratum1/
  - /docs/roadmap/site-work/mobile/stratum1/plan/
weight: 16
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 14
---

# Stratum 1 NTP: Project Plan

Raspberry Pi Zero-based Stratum 1 NTP server with GPS time source.

Part of `deevnet-image-factory`.

**Roadmap item:** [Stratum 1 NTP](/docs/roadmap/stratum1/)

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

- ⏳ Define time accuracy requirements {{< added "2026-01-22" >}}
- ⏳ Define GPS antenna placement constraints {{< added "2026-01-22" >}}
- ⏳ Define telemetry and alerting requirements {{< added "2026-01-22" >}}

---

## Hardware ⏳

- ⏳ Pi Zero W/2W selection {{< added "2026-01-22" >}}
- ⏳ GPS HAT/module selection {{< added "2026-01-22" >}}
- ⏳ Hardware acquisition {{< added "2026-01-22" >}}

---

## Image Build ⏳

- ⏳ Base Pi Zero image {{< added "2026-01-22" >}}
- ⏳ GPS daemon (gpsd) configuration {{< added "2026-01-22" >}}
- ⏳ NTP/Chrony configuration for Stratum 1 {{< added "2026-01-22" >}}
- ⏳ Telemetry and alerting configuration {{< added "2026-01-22" >}}
- ⏳ Test scripts for time accuracy validation {{< added "2026-01-22" >}}

---

## Deployment ⏳

- ⏳ Network position and VLAN assignment {{< added "2026-01-22" >}}
- ⏳ Client configuration to use Stratum 1 {{< added "2026-01-22" >}}
- ⏳ Build documentation {{< added "2026-01-04" >}}
