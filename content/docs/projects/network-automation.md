---
title: "Network Automation"
weight: 19
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 6
---

# Network Automation

Gaps in the network's automation found while building it: manual steps, idempotency, API
limits, and checks on every change.

**Roadmap item:** [Network Automation](/docs/roadmap/infrastructure/substrate/network-automation/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Automation Improvements ⏳

Improvements identified during the network migration and authority transition work. Non-blocking enhancements — the network is fully functional, but these items improve automation coverage, idempotency, and reduce manual steps for future rebuilds.

- ⏳ Automate OPNsense interface assignment and IP config via SSH (eliminate manual GUI steps — OPNsense 25.7 has no API for this)
- ⏳ TP-Link SG2218 cliconf idempotency (proper config diff support in the Ansible cliconf plugin)
- ⏳ OPNsense automation filter API investigation (addRule saves but doesn't compile to pf on 25.7.10)
- ⏳ Omada SSID VLAN provisioning via controller after AP firmware update
- ⏳ Replace curl-based Omada API tasks with Ansible uri module (eliminate command-line secret exposure)
- ⏳ Checks on every pull request (GitHub Actions): `ansible-playbook --syntax-check`, `packer validate` and the docs build, so the change-management validation checklist is not only manual
