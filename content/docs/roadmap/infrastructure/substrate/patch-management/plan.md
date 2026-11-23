---
title: "Patch Management: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/software-discovery/
  - /projects/software-discovery/
  - /docs/projects/patch-awareness/
  - /projects/patch-awareness/
  - /docs/roadmap/infrastructure/substrate/software-discovery/plan/
  - /docs/roadmap/infrastructure/substrate/patch-awareness/plan/
weight: 9
tasks_completed: 3
tasks_in_progress: 0
tasks_planned: 30
---

# Patch Management: Project Plan

Keeping what the substrate runs up to date, systematically: know what is running, hear when it
needs attention, patch it on a cycle, unattended where that is safe, and keep the take-home images
current. This is the [Discovery](/docs/policies/lifecycle-management/discovery/) and Patch stages
of Lifecycle Management, built.

**Roadmap item:** [Patch Management](/docs/roadmap/infrastructure/substrate/patch-management/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

**Patching today depends on someone remembering to look.** The Software Catalog is the system of
record for versions, but it is assembled by hand from inventory pins, role defaults, lockfiles and
change records. Advisories are picked up when a component is upgraded. No role or playbook applies
updates, so each patch is a one-off change record.

That leaves these gaps, each closed by a version after the first:
- **A pin is intent, not fact.** It says what the automation deploys, not what is running after a
  manual upgrade, a failed play or a host rebuilt by hand. Much is never written down at all:
  OPNsense's bundled packages, the FRR on the tenant hypervisor, Podman on the VMs, the OS on three
  of the four Pis and the Builder's own Fedora release are "not recorded" in the catalog today.
- **Nothing says when an update is waiting.** A new OPNsense patch is found only by looking.
  Release and advisory sources are not recorded, and end of life is noticed late.
- **Applying a patch has no rhythm.** No cycle, no order, no standing procedure per kind of host.
- **The take-home images age.** A Pi or VM image in the tenant downloads keeps its base OS from the
  day it was built.

**In Scope**
- Read-only collection from every substrate system the Builder can reach, with the credentials
  automation already holds, compared against the catalog and the inventory pins
- An email to the operator when an update is waiting, first from what each system reports, then
  from release and advisory sources for every catalog item, with end-of-life dates
- A monthly patch cycle for substrate hosts and the Pi lab, with a procedure and a way back for each
  kind of host
- Unattended security updates where a failure cannot take the site down
- The take-home images Deevnet publishes in the tenant downloads

**Out of Scope**
- Tenant workloads. What a tenant runs is the tenant's to track and patch.
- The travel router, which automation doesn't manage. It stays a manual entry.
- A local package mirror. It stays an evaluation candidate
  ([Substrate package mirror](/docs/platforms/evaluations/software/management-plane/package-mirror/));
  the cycle assumes internet access, as patching does today.
- Upgrades to a new line. Those are evaluated first, as Lifecycle Management's Upgrade stage requires,
  and go through their own change.

---

## Versions

### v1, know what runs (current)

A dated report of what is actually running, compared with the catalog.

**Done when:**

- ✅ The catalog's rows are moved into a data file the page renders from, so a report can be
  compared with it mechanically. The page's grouping, columns and version-source terms stay as
  they are.
- ✅ What was deployed as `-latest` is pinned: `deevnet-broker-account` (the `vernemq` role),
  `deevnet-log-user` (the `victorialogs` role), and the `deevnet-kit`, `deevnet-log-user` and
  `deevnet-log-bridge` binaries the Pi backend image fetches. The reference tenant's provider
  constraint moves to the line it actually runs. Each is pinned to the file `-latest` pointed at;
  the reference tenant had already moved to `~> 0.5`, locked at 0.5.0
- ✅ Every in-house repository is licensed: a LICENSE file in `deevnet-provisioning-api`,
  `terraform-provider-deevnet`, `deevnet-log-bridge`, `deevnet-container-image-factory` and the
  tenant repositories, and `galaxy.yml` agreeing with `LICENSE` in the `deevnet.mgmt` and
  `deevnet.net` collections. Every Deevnet repository is Apache-2.0
- ⏳ **Core router collector:** `opnsense-version -v` for the release and base, and `pkg info` for
  the bundled packages in use (Kea, Unbound) and every installed `os-*` plugin. `opnsense-diag.sh`
  already gathers the first.
- ⏳ **Hypervisor collector:** `pveversion -v`, which covers Proxmox VE, the kernel, FRR and the
  SDN packages.
- ⏳ **Substrate service VM and Builder collector:** `/etc/os-release`, the kernel, the Podman
  version, and the image of every running container, read from the container and not from the
  unit file.
- ⏳ **Network device collector:** the switch's `show system-info`, and the controller and AP
  versions from the Omada Open API.
- ⏳ **Raspberry Pi collector:** `/etc/os-release` and the kernel, for every Pi that answers. A Pi
  that doesn't answer is reported as unreachable, not skipped silently.
- ⏳ One dated report per run, kept on the Builder, listing for each item the observed version and
  the catalog's version, and for each running container the image its role pins, with every
  mismatch called out.
- ⏳ The report runs from one `make` target, and after any change record that upgrades something,
  so the catalog is updated in the same change.

**The choices, the owner's, 2026-11-23.** The report has its own `make discover` target;
[Build Verification](/docs/roadmap/infrastructure/substrate/management-plane/) includes it when that
report is built, not before. Pins are compared for containers only: an OS or firmware has no pin to
compare, only its catalog row. Reports stay on the Builder, since the docs are public and a report
lists the exact version of everything the site runs.

**Not in v1:** release and advisory sources (v2); applying anything. Discovery reports; changes go
through change management.

### v2, told when an update is waiting

Most of the substrate can say for itself that an update is waiting, so the operator is told by
email rather than finding out. Comparing against upstream is v3; this asks each system.

**Done when:**

- ⏳ Each v1 collector also reports the updates waiting, and which of them are security updates:
  the core router through OPNsense's firmware update check, the Fedora substrate service VMs and the
  Builder through `dnf`, the Pis through `apt`, and the switch and AP through the firmware upgrades
  the Omada controller offers. The hypervisors already email their own waiting package updates
  through Proxmox's notifications (CHG-0079); they are counted in the report, not mailed twice.
- ⏳ A daily timer on the Builder runs the collectors.
- ⏳ The Builder sends mail to the operator's address, the one the hypervisors' notifications use.
- ⏳ An update is mailed once, the day it is first seen, not every day it waits. Security updates
  are marked as such in the subject.
- ⏳ An update still waiting after 30 days is mailed again, and a system that didn't answer is
  mailed as unreachable.

**Not in v2:** software that can't report its own updates (v3); a phone or ntfy alert, which waits
for operator alerting on the Observability item.

### v3, told when upstream moves on

What can't report its own updates is watched at the source: the container images (OpenBao,
VerneMQ, silo, Grafana, the VictoriaMetrics services, Alertmanager, ntfy), the Omada controller,
and Deevnet's own pinned releases. The same mail carries it.

**Done when:**

- ⏳ Each catalog item's **release source** and **advisory source** are recorded, as two new
  catalog columns. For OPNsense, one entry covers its bundled services too.
- ⏳ The daily run checks every source (feeds where they exist, a checked list where they don't),
  with each source's last-seen release.
- ⏳ A release newer than the running version is mailed once, as in v2.
- ⏳ Each new release is triaged as [Discovery](/docs/policies/lifecycle-management/discovery/)
  defines it (patch, new line, end of life, archived, advisory, or nothing relevant), and the outcome
  recorded, so nothing is triaged twice.
- ⏳ End-of-life dates are recorded for the lines in use, and any within six months mailed.

**Not in v3:** response times by severity (v4 sets the cycle they are measured against).

### v4, apply on a cadence

Substrate hosts are patched within their approved line on a monthly cycle, in a fixed order, each
with a way back.

**Done when:**

- ⏳ The cycle is written in the runbook's [Patching](/docs/runbook/substrate/lifecycle/patching/)
  page: monthly, in the order substrate service VMs and the Builder, then the hypervisors one at a
  time, then the core router, then the Pi lab. A waiting security update the operator judges
  urgent starts an out-of-cycle run.
- ⏳ A playbook patches the Fedora substrate service VMs and the Builder one host at a time:
  update, reboot when the kernel or a library in use changed, and a health check before the next
  host. A snapshot is taken before each, and kept until the next cycle.
- ⏳ A runbook procedure patches each hypervisor within its Proxmox VE line, one at a time, with
  its VMs shut down or moved first and verified after.
- ⏳ A runbook procedure patches the core router within its OPNsense line: `make backup-router`
  before and after, and the previous release as the way back.
- ⏳ A playbook patches the Pis in the Pi lab, and reports any that didn't answer.
- ⏳ A monthly cycle is one change record, of a pre-approved standard type defined in
  [Change Management](/docs/policies/change-management/), rather than a bespoke record per host.
- ⏳ Each cycle ends with the v1 report run and the catalog updated from it.

**Not in v4:** anything unattended (v5); switch and AP firmware, which stay per-change upgrades.

### v5, unattended where safe

Security updates go in without the operator where a failure cannot take the site down.

**Done when:**

- ⏳ Security-only automatic updates on the Fedora substrate service VMs, staggered so no two run
  at once, outside the hours the site is in use.
- ⏳ Every unattended run is reported in the daily mail; a failure or a pending reboot is told, not
  found.
- ⏳ What is **never** patched unattended is written down, each with its reason: the hypervisors,
  the core router, switch and AP firmware, and OpenBao.

### v6, shipped images stay current

The take-home images in the tenant downloads are rebuilt so they don't age.

**Done when:**

- ⏳ Every take-home image, the Pi's and each virtual machine format, is rebuilt with the monthly
  cycle, and after any security update affecting it, and passes its self-test before it is
  published.
- ⏳ Each image states its base OS date, on the image and in the tenant downloads.
- ⏳ The tenant guide says how an owner sees that a newer image exists, and how they update one
  already flashed.

### Later

- Operator alerts by phone (ntfy) instead of mail, once operator alerting is decided on the
  [Observability](/docs/roadmap/infrastructure/substrate/observability/) item
- Dependency and container image vulnerability scans before a release is staged
  ([Vulnerability Management](/docs/policies/risk-management/vulnerability-management/))
- Response times by severity, measured against the cycle
- A local package mirror, if the mirror evaluation is approved
