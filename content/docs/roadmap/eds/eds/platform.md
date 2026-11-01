---
title: "Platform"
weight: 6
milestones:
  - title: "The broker is Deevnet's; the tenant and its workload (EdS ADR-0003)"
    group: "At the factory"
    status: done
    date: "2026-09-07"
  - title: "The relay Pi, with a leg on the home network; EdS's own Pi images (EdS ADR-0010, ADR-0015)"
    group: "At the factory"
    status: done
    date: "2026-10-10"
  - title: "A deploy sends only what changed (EdS INC-0002)"
    group: "At the factory"
    status: done
    date: "2026-10-24"
  - title: "Keep, retire or move the tenant, its workload and the relay (EdS CHG-0028)"
    group: "At the factory"
    status: planned
  - title: "The whole back end on one Pi: in service, the record awaiting its evidence (EdS ADR-0033, CHG-0028)"
    group: "At home"
    status: active
  - title: "A Deevnet Pi, under the tenant's site-less names (EdS CHG-0042)"
    group: "At home"
    status: done
    date: "2026-10-29"
  - title: "On its cable alone, the radio off (EdS CHG-0046)"
    group: "At home"
    status: done
    date: "2026-10-30"
  - title: "The backend image rebuilt with all of it (EdS CHG-0048)"
    group: "At home"
    status: active
  - title: "nginx on 80 and 443; Grafana by name (EdS CHG-0042)"
    group: "At home"
    status: planned
  - title: "The certificate named for the host, `backend.eds.deevnet.net` (EdS CHG-0042)"
    group: "At home"
    status: planned
  - title: "The Builder's maintenance window onto the home network (EdS ADR-0053)"
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

{{< milestones group="At the factory" >}}

---

## At home 🔄

{{< milestones group="At home" >}}
