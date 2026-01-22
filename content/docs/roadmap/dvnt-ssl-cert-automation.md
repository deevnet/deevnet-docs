---
title: "DVNT SSL Cert Automation"
weight: 5
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 12
---

# DVNT SSL Cert Automation

Automated SSL certificate provisioning and renewal for dvnt (home) substrate services.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

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

- ⏳ Proxmox VE admin UI (pve.dvnt.deevnet.net)
- ⏳ OPNsense admin UI (opnsense.dvnt.deevnet.net)
- ⏳ Omada Controller UI (omada.dvnt.deevnet.net)

---

## Certificate Lifecycle ⏳

Automated renewal and distribution.

- ⏳ ACME client deployment (certbot, acme.sh, or step CLI)
- ⏳ Automated certificate renewal via cron/systemd timer
- ⏳ Certificate deployment playbook
- ⏳ Expiration monitoring and alerting
- ⏳ Document manual renewal procedure (fallback)
