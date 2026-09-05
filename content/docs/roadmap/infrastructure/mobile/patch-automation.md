---
title: "Patch Automation"
weight: 2
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 16
---

# Patch Automation

Automated patching strategies, firmware upgrades, and automation improvements for substrate infrastructure components.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Define and implement consistent patching strategies across all substrate components to maintain security posture while minimizing downtime. Includes firmware upgrades and automation improvements identified during the network build.

**In Scope**
- Patching procedures for all infrastructure components
- Firmware upgrades for network devices
- Automation improvements (idempotency, API gaps, manual step elimination)
- Rollback procedures
- Patch testing requirements

**Out of Scope**
- Application-level updates (handled per-tenant)
- Zero-day emergency response (separate runbook)

---

## Requirements ⏳

- ⏳ Define maintenance windows per component type
- ⏳ Define patch testing requirements
- ⏳ Define rollback criteria

---

## Firmware Upgrades ⏳

Device firmware updates required for full automation coverage.

- ⏳ EAP650-Outdoor AP firmware update (1.0.4 → latest) — current firmware doesn't accept VLAN config from Omada 6.1 controller, requiring manual standalone UI configuration
- ⏳ SG2218 Access Switch firmware update — evaluate newer firmware for improved CLI compatibility and Omada integration

---

## Automation Improvements ⏳

Improvements identified during the network migration and authority transition work. Non-blocking enhancements — the network is fully functional, but these items improve automation coverage, idempotency, and reduce manual steps for future rebuilds.

- ⏳ Automate OPNsense interface assignment and IP config via SSH (eliminate manual GUI steps — OPNsense 25.7 has no API for this)
- ⏳ TP-Link SG2218 cliconf idempotency (proper config diff support in the Ansible cliconf plugin)
- ⏳ OPNsense automation filter API investigation (addRule saves but doesn't compile to pf on 25.7.10)
- ⏳ Omada SSID VLAN provisioning via controller after AP firmware update
- ⏳ Replace curl-based Omada API tasks with Ansible uri module (eliminate command-line secret exposure)

---

## Patching Strategies ⏳

Ongoing maintenance and security updates.

- ⏳ Patching Strategy - Switches
- ⏳ Patching Strategy - Proxmox VE
- ⏳ Patching Strategy - Firewall/Core router
- ⏳ Patching Strategy - Linux packages

---

## Documentation ⏳

- ⏳ Patching runbook
- ⏳ Rollback procedures
