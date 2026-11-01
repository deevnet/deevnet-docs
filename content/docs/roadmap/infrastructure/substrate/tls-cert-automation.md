---
title: "TLS Cert Automation"
aliases:
  - /docs/roadmap/infrastructure/ssl-cert-automation/
  - /docs/roadmap/infrastructure/tls-cert-automation/
weight: 9
milestones:
  - title: "The Deevnet Root CA and Mobile Site CA, made offline (CHG-0033)"
    status: done
    date: "2026-10-05"
  - title: "Tenant CAs keyed outside OpenBao (CHG-0036)"
    status: done
    date: "2026-10-25"
  - title: "The Deevnet Root trusted everywhere the site builds"
    status: done
    date: "2026-10-05"
  - title: "Workloads cloned before the re-root replaced"
    status: active
  - title: "Substrate Services"
    status: done
    date: "2026-10-05"
  - title: "Device Identity"
    status: planned
  - title: "Later"
    status: planned
---

# TLS Cert Automation

Every certificate the site serves chains to the **Deevnet Root CA**, kept offline with the Mobile
Site CA ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/),
[CHG-0033](/docs/changes/2026/0033-deevnet-pki/)). The Mobile Substrate CA signs every substrate
certificate on the control node, OpenBao's listener included, and `certs.yml` renews them. The
Builder, the hypervisors and every management-plane VM trust the root at the OS level; tenants trust
it as `deevnet-root-ca.pem`. Proxmox, the core router and the Omada controller serve site
certificates, and every client verifies them
([Certificates](/docs/runbook/substrate/certificates/)). The Tenant Device CA is in OpenBao, waiting
for device enrollment.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

{{< milestones >}}

**Project plan:** [TLS Cert Automation](/projects/tls-cert-automation/)
