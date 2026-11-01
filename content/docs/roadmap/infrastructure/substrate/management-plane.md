---
title: "Extended Management Plane"
aliases:
  - /docs/roadmap/infrastructure/mobile/management-plane/
weight: 2
milestones:
  - title: "Management services on six domain VMs (CHG-0008)"
    status: done
    date: "2026-09-16"
  - title: "Requirements"
    status: active
  - title: "Centralized logging: the log store, tenant scope, the MQTT bridge, Grafana"
    status: done
    date: "2026-09-24"
  - title: "Telemetry"
    status: active
  - title: "Alerting"
    status: planned
  - title: "Network Management"
    status: planned
  - title: "Substrate secrets in Ansible Vault, guarded on every commit"
    status: done
    date: "2026-03-14"
  - title: "OpenBao deployed; the API reads its credentials from it (CHG-0010)"
    status: done
    date: "2026-09-17"
  - title: "Builds take their secrets from OpenBao, none on disk (CHG-0026)"
    status: done
    date: "2026-09-25"
  - title: "OpenBao's keys from the vault, its access bound and audited (CHG-0036)"
    status: done
    date: "2026-10-25"
  - title: "Secrets: the Shamir seal and the rebuild drill"
    status: active
  - title: "Identity Management"
    status: planned
  - title: "Each SSID's reach checked from a real client"
    status: done
    date: "2026-09-23"
  - title: "Build Verification"
    status: active
  - title: "Documentation"
    status: planned
  - title: "Nightly encrypted backups, one restore rehearsed (CHG-0039)"
    status: done
    date: "2026-10-07"
---

# Extended Management Plane

Extended management services for the mobile (mobile) site — logging, telemetry, alerting, secrets, and identity. Builds on the core substrate once it is operational.

- **GitHub:** https://github.com/deevnet/ansible-collection-deevnet.mgmt
- **Documentation:** https://deevnet.github.io/deevnet-docs/

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [Extended Management Plane](/projects/management-plane/)
