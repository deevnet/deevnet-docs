---
title: "SSL Cert Automation"
weight: 5
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 16
---

# SSL Cert Automation

Automated SSL certificate provisioning and renewal for substrate services.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Eliminate browser security warnings and enable secure communication between substrate services by deploying an internal Certificate Authority and automating certificate lifecycle management.

**In Scope**
- Internal CA deployment and trust distribution
- SSL certificates for infrastructure web UIs (Proxmox, OPNsense, Omada)
- Automated certificate renewal
- Expiration monitoring

**Out of Scope**
- Public-facing certificates (use Let's Encrypt separately)
- Client certificate authentication
- Code signing certificates

---

## Requirements ⏳

- ⏳ Define certificate naming conventions
- ⏳ Define certificate validity periods
- ⏳ Define renewal thresholds and alerting

---

## Certificate Authority ⏳

Internal CA infrastructure for issuing trusted certificates.

- ⏳ Evaluate CA options (step-ca, smallstep, CFSSL)
- ⏳ Deploy internal CA on bootstrap node
- ⏳ Distribute root CA to substrate hosts
- ⏳ Configure browser/OS trust stores

---

## Infrastructure Services ⏳

SSL certificates for core infrastructure web UIs.

- ⏳ Proxmox VE admin UI (pve.home.deevnet.net)
- ⏳ OPNsense admin UI (opnsense.home.deevnet.net)
- ⏳ Omada Controller UI (omada.home.deevnet.net)

---

## Certificate Lifecycle ⏳

Automated renewal and distribution.

- ⏳ ACME client deployment (certbot, acme.sh, or step CLI)
- ⏳ Automated certificate renewal via cron/systemd timer
- ⏳ Certificate deployment playbook
- ⏳ Expiration monitoring and alerting

---

## Documentation ⏳

- ⏳ Certificate management runbook
- ⏳ Manual renewal procedure (fallback)
