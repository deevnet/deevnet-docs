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
| OS packages, at install | The staged install tree on the artifact server — no internet needed | [Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/) |
| OS packages, after install | Public Fedora mirrors — the host needs internet access | Per change record |
| Proxmox VE (both hypervisors) | Proxmox's Debian repositories, in place. A major version is only reached through the one before it, following Proxmox's upgrade path (`pve8to9` before 8 → 9) | Per change record; the 8 → 9 move was the [Hypervisor Uplift](/docs/roadmap/site-work/mobile/hypervisor-uplift/plan/) |
| OPNsense (core router) | OPNsense's firmware updates, in place, one major release after another in order | [Core Router Patch](/docs/runbook/substrate/lifecycle/core-router-patch/), a change record each time |
| Omada controller | A staged image on the artifact server | [Omada Controller Upgrade](/docs/runbook/substrate/lifecycle/omada-controller-upgrade/) |
| Switch and AP firmware | Firmware staged on the artifact server | Per change record: [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/) (switch), [CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/) (AP) |

---

## Updates waiting

**The update watcher on the Builder asks every substrate host once a day what updates it has
waiting, and says so at login.** It runs as `deevnet-watch`, whose key each host pins to one
read-only check ([CHG-0082](/docs/changes/2026/0082-update-watcher/)).

| What | Where |
|---|---|
| Everything waiting now | `/srv/updates/latest.txt`, rewritten each run |
| What was new on a day | `/srv/updates/YYYY-MM-DD.txt` |
| The banner | Printed in every interactive login shell on the Builder while something new is unacknowledged: the scoreboard below |

**The scoreboard counts what waits on each system**, grouped as service VMs, Builder, hypervisors and
network, and marks `new` the systems with news not yet acknowledged. `latest.txt` and each day's report
open with it too.

```text
                Major  Minor  Security
Service VMs
  dv02idn001v01     1    139        56  new
  dv02obj001v01     -      -         -
Builder
  dv00bld001p01    17    561       239  new
Network
  dv02cor002p01     -      1         -  new  OPNsense 26.7.10
Total              ...
```

| Column | Counts |
|---|---|
| Major | updates that change the epoch or the first version field: kernel 6.17 to 7.3. A first field that is a date (linux-firmware, tzdata) does not count; an OPNsense release line does |
| Minor | every other update. Major and Minor together are every update waiting |
| Security | the updates, of either kind, that fix a security advisory |

A system that does not answer, or answers without saying what is waiting, shows as `no answer`.

What counts as new: a security update, a host that had nothing waiting and now has, a new OPNsense
point release or line (from OPNsense's published releases, against the newest discovery report), new
firmware for a device the Omada controller manages, a system that stopped answering, and anything
still waiting after 30 days. The hypervisors are listed but are not news: Proxmox VE notifies its own.

In `ansible-collection-deevnet.builder`:

```bash
make update-watch-ack       # the report is read: clear the banner until something is new
make update-watch-now       # run it now, instead of waiting for the timer
make update-watch-dry-run   # print what it would write, writing nothing
```

---

## What is not covered

**Post-install updates need the internet.** There is no local package mirror, so an air-gapped site
cannot patch its hosts. The options (accept internet access, a full local mirror at roughly 200 GB
per Fedora release, or security updates only) are recorded in the
[Substrate package mirror](/docs/platforms/evaluations/software/management-plane/package-mirror/)
candidate.

**There is no patch cycle yet.** A monthly cycle in a fixed order, a procedure and a way back for
each kind of host, unattended security updates where that is safe, and knowing when a patch is
needed are the [Patch Management](/docs/roadmap/infrastructure/substrate/patch-management/)
roadmap project.
