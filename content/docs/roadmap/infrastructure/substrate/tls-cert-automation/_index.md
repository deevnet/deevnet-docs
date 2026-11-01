---
title: "TLS Cert Automation"
bookCollapseSection: true
aliases:
  - /docs/roadmap/infrastructure/ssl-cert-automation/
  - /docs/roadmap/infrastructure/tls-cert-automation/
weight: 9
milestones:
  - title: "Deevnet's own root and site certificate authorities created and kept offline (CHG-0033)"
    status: done
    date: "2026-10-05"
  - title: "Tenant certificate authorities' keys generated outside the OpenBao secrets manager (CHG-0036)"
    status: done
    date: "2026-10-25"
  - title: "Every machine the site builds trusts the Deevnet root certificate"
    status: done
    date: "2026-10-05"
  - title: "Tenant VMs that trust only the retired root certificate replaced"
    status: active
  - title: "Every infrastructure service and appliance on the site serves a Deevnet certificate, and its clients verify it"
    status: done
    date: "2026-10-05"
  - title: "IoT devices get their own certificates through the Deevnet API and use them to log in to the MQTT broker"
    status: planned
  - title: "Automatic certificate renewal, expiry monitoring, and a clean new root once device certificates work"
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

**Project plan:** [TLS Cert Automation](/docs/roadmap/infrastructure/substrate/tls-cert-automation/plan/)
