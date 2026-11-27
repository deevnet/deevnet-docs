---
title: "Network Automation: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/network-automation/
  - /projects/network-automation/
weight: 19
tasks_completed: 1
tasks_in_progress: 0
tasks_planned: 5
---

# Network Automation: Project Plan

Gaps in the network's automation found while building it: manual steps, idempotency, API
limits, and checks on every change.

**Roadmap item:** [Network Automation](/docs/roadmap/infrastructure/substrate/network-automation/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Automation Improvements 🔄

Improvements identified during the network migration and authority transition work. Non-blocking enhancements — the network is fully functional, but these items improve automation coverage, idempotency, and reduce manual steps for future rebuilds.

- ⏳ Automate OPNsense interface assignment and IP config via SSH (eliminate manual GUI steps — OPNsense 25.7 has no API for this) {{< added "2026-03-25" >}}
- ⏳ TP-Link SG2218 cliconf idempotency (proper config diff support in the Ansible cliconf plugin) {{< added "2026-03-21" >}}
- ⏳ OPNsense automation filter API investigation (addRule saves but doesn't compile to pf on 25.7.10) {{< added "2026-03-25" >}}
- ⏳ Omada SSID VLAN provisioning via controller after AP firmware update {{< added "2026-03-25" >}}
- ⏳ Replace curl-based Omada API tasks with Ansible uri module (eliminate command-line secret exposure) {{< added "2026-03-25" >}}
- ✅ Checks on every pull request (GitHub Actions): `ansible-playbook --syntax-check`, `packer validate` and the docs build, so the change-management validation checklist is not only manual. Each collection and the image factory run `make check` in CI, and this site builds on every pull request {{< added "2026-09-27" >}}
