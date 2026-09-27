---
title: "VyOS"
weight: 1
bookCollapseSection: true
---

# VyOS

| | |
|---|---|
| **Role** | Core router, in place of OPNsense |
| **Current** | {{< status-badge "on-hold" "On hold" >}} Not yet evaluated |

OPNsense has served well for production routing. The lack of automated installation (no PXE) is **not a show-stopper** for the MVP—a fresh OPNsense install is treated as a manual prerequisite to the building/recovery plan, alongside factory-resetting the access switch and AP.

## Original Motivation

| Requirement | OPNsense | VyOS |
|-------------|----------|------|
| Automated install | No PXE, manual USB only | cloud-init + staged ISO |
| Air-gap recovery | Manual reinstall | Staged ISO, automated |
| Config-as-code | API-based | Native CLI + Ansible |
| Day-2 automation | Good (Ansible) | Excellent (vyos.vyos) |
| WebUI | Yes | No (CLI-centric) |

## Why On Hold

- **OPNsense Day-2 automation is mature** — the `deevnet.net` Ansible collection handles DNS, DHCP, firewall, and WoL configuration
- **Manual install is an accepted MVP prerequisite** — same category as factory-resetting the switch and AP before the automated build begins
- **WebUI remains valuable** for visual firewall auditing and one-off diagnostics
- **VyOS rolling release risk** — LTS requires subscription; rolling is less predictable for a core network device
- **No pressing need** — the current OPNsense deployment is stable and well-automated for Day-2 operations

## Conditions to Revisit

- OPNsense automation becomes insufficient for a new requirement
- VyOS LTS becomes freely available
- A use case arises where CLI-only management is a clear advantage

## Revisions

None yet.
