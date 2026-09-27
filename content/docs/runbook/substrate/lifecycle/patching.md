---
title: "Patching"
weight: 1
aliases:
  - /docs/runbook/lifecycle/patching/
  - /docs/runbook/patching/
---

# Patching

Day 2 maintenance and security updates for substrate hosts.

---

## How patching is done today

No role or playbook applies updates. A patch is a change, and goes through
[Change Management](/docs/policies/change-management/) like any other: a change record, the
update applied to the host, and verification afterwards. How a patch is chosen is
[Vulnerability Management](/docs/policies/risk-management/vulnerability-management/).

| What | Where it comes from | Procedure |
|------|---------------------|-----------|
| OS packages, at install | The staged install tree on the artifact server — no internet needed | [Build a Management-Plane VM](/docs/runbook/substrate/building-recovery/build-management-vm/) |
| OS packages, after install | Public Fedora mirrors — the host needs internet access | Per change record |
| Proxmox VE (both hypervisors) | Proxmox's Debian repositories, in place. A major version is only reached through the one before it, following Proxmox's upgrade path (`pve8to9` before 8 → 9) | Per change record; the 8 → 9 move was the [Hypervisor Uplift](/docs/roadmap/infrastructure/mobile/hypervisor-uplift/) |
| OPNsense (core router) | OPNsense's firmware updates, in place, one major release after another in order | Per change record |
| Omada controller | A staged image on the artifact server | [Omada Controller Upgrade](/docs/runbook/substrate/lifecycle/omada-controller-upgrade/) |
| Switch and AP firmware | Firmware staged on the artifact server | Per change record: [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/) (switch), [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) (AP) |

---

## What is not covered

**Post-install updates need the internet.** There is no local package mirror, so an air-gapped site
cannot patch its hosts. The options (accept internet access, a full local mirror at roughly 200 GB
per Fedora release, or security updates only) are recorded in the
[Substrate package mirror](/docs/platforms/evaluations/software/management-plane/package-mirror/)
candidate. Maintenance windows, patch testing, rollback criteria and automated patching are the
[Patch Automation](/docs/roadmap/infrastructure/mobile/patch-automation/) roadmap project.
