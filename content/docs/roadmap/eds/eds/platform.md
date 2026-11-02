---
title: "Platform"
weight: 6
waypoints:
  - title: "EdS set up as a Deevnet tenant with its own workload, using Deevnet's MQTT broker (EdS ADR-0003)"
    group: "At the factory"
    status: done
    date: "2026-09-07"
  - title: "EdS's relay Pi with a connection onto the home network, and EdS's own Pi images (EdS ADR-0010, ADR-0015)"
    group: "At the factory"
    status: done
    date: "2026-10-10"
  - title: "An EdS deploy sends only what changed (EdS INC-0002)"
    group: "At the factory"
    status: done
    date: "2026-10-24"
  - title: "Decide whether to keep, retire or move EdS's tenant, workload and relay Pi on the mobile site (EdS CHG-0028)"
    group: "At the factory"
    status: planned
  - title: "All of EdS's back end on one Pi at home: in service, the change record awaiting its evidence (EdS ADR-0033, CHG-0028)"
    value: [works-anywhere]
    group: "At home"
    status: active
  - title: "EdS's home Pi uses Deevnet certificates, under names not tied to a site (EdS CHG-0042)"
    value: [works-anywhere]
    group: "At home"
    status: done
    date: "2026-10-29"
  - title: "EdS's home Pi runs on its network cable alone, the radio off (EdS CHG-0046)"
    group: "At home"
    status: done
    date: "2026-10-30"
  - title: "EdS's home Pi image rebuilt with all of its back end (EdS CHG-0048)"
    group: "At home"
    status: done
    date: "2026-11-01"
  - title: "EdS's home Pi serves through nginx on ports 80 and 443, with Grafana by name (EdS CHG-0042)"
    group: "At home"
    status: planned
  - title: "EdS's home Pi certificate named for the host, `backend.eds.deevnet.net` (EdS CHG-0042)"
    group: "At home"
    status: planned
  - title: "A maintenance window that lets the build server reach the home network (EdS ADR-0053)"
    group: "At home"
    status: planned
---
# Platform

Where EdS runs: the tenant's workload and the broker at the factory, the relay Pi, and the backend Pi at home.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---
## Project Vision & Scope

EdS runs at the factory as a Deevnet tenant and at home on one Pi, under Deevnet's certificates.

**In Scope**
- The tenant, the relay Pi and the backend Pi
- EdS's Pi images
- Its certificates

**Out of Scope**
- The Deevnet PKI itself: Infrastructure Automation

---

## At the factory 🔄

{{< waypoints group="At the factory" >}}

---

## At home 🔄

{{< waypoints group="At home" >}}
