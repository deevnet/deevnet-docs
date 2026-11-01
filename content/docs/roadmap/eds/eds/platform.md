---
title: "Platform"
weight: 6
tasks_completed: 5
tasks_in_progress: 2
tasks_planned: 4
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

- ✅ The broker is Deevnet's; the tenant and its workload (EdS ADR-0003)
- ✅ The relay Pi, with a leg on the home network; EdS's own Pi images (EdS ADR-0010, ADR-0015)
- ✅ A deploy sends only what changed (EdS INC-0002)
- ⏳ Keep, retire or move the tenant, its workload and the relay (EdS CHG-0028)

---

## At home 🔄

- 🔄 The whole back end on one Pi: in service, the record awaiting its evidence (EdS ADR-0033, CHG-0028)
- ✅ A Deevnet Pi, under the tenant's site-less names (EdS CHG-0042)
- ✅ On its cable alone, the radio off (EdS CHG-0046)
- 🔄 The backend image rebuilt with all of it (EdS CHG-0048)
- ⏳ nginx on 80 and 443; Grafana by name (EdS CHG-0042)
- ⏳ The certificate named for the host, `backend.eds.deevnet.net` (EdS CHG-0042)
- ⏳ The Builder's maintenance window onto the home network (EdS ADR-0053)
