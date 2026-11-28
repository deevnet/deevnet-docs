---
title: "VM Hardware Profile"
weight: 12
value: [contained-failure, rebuild-from-code]
waypoints:
  - title: "One declared hardware profile for every VM the site builds, with inventory as its only source (ADR-0046)"
    added: "2026-11-21"
    value: [rebuild-from-code]
    status: done
    date: "2026-11-21"
  - title: "The site's service VMs moved off the emulated LSI disk controller that panicked under backup load (CHG-0093, INC-0006)"
    added: "2026-11-26"
    status: done
    date: "2026-11-26"
  - title: "Every VM builder applies the hardware profile, and checks each VM it builds before its first start (CHG-0098, CHG-0101)"
    added: "2026-11-27"
    value: [rebuild-from-code]
    status: done
    date: "2026-11-27"
  - title: "Tenant workloads and the standby build server moved to the hardware profile, so every VM matches it (CHG-0097, CHG-0100)"
    added: "2026-11-27"
    status: done
    date: "2026-11-27"
  - title: "A VM whose hardware drifts from the profile shows on the build server's login banner within five minutes (CHG-0101)"
    added: "2026-11-27"
    value: [no-surprises]
    status: done
    date: "2026-11-27"
---

# VM Hardware Profile

Every VM Deevnet builds on a Proxmox hypervisor, service VMs and tenant workloads alike, has one
declared virtual hardware profile: its disk controller, firmware and machine type, read from
inventory. The builders apply it and check what they built, and the health watcher reports any VM
that drifts. It was decided in
[ADR-0046](/docs/architecture/decisions/substrate/0046-vm-hardware-profile/) after the API VM's
default LSI controller panicked under load
([INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/)), and accepted on 2026-11-27.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< waypoints >}}
