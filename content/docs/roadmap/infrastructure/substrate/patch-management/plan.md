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
tasks_completed: 17
tasks_in_progress: 1
tasks_planned: 17
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
  OPNsense's bundled packages, the FRR on the tenant hypervisor, Podman on the VMs and the
  Builder's own Fedora release are "not recorded" in the catalog today.
- **Nothing says when an update is waiting.** A new OPNsense patch is found only by looking.
  Release and advisory sources are not recorded, and end of life is noticed late.
- **Applying a patch has no rhythm.** No cycle, no order, no standing procedure per kind of host.
- **The take-home images age.** A Pi or VM image in the tenant downloads keeps its base OS from the
  day it was built.

**In Scope**
- Read-only collection from every substrate system the Builder can reach, with the credentials
  automation already holds, compared against the catalog and the inventory pins
- A report and a login banner for the operator when an update is waiting, first from what each
  system reports, then from release and advisory sources for every catalog item, with end-of-life
  dates
- A monthly patch cycle for substrate hosts, with a procedure and a way back for each
  kind of host
- Unattended security updates where a failure cannot take the site down
- The take-home images Deevnet publishes in the tenant downloads

**Out of Scope**
- Tenant workloads. What a tenant runs is the tenant's to track and patch.
- The travel router, which automation doesn't manage. It stays a manual entry.
- The Pi lab. Its Pis take whatever microSD card an experiment needs that day, so there is no
  expected OS to check or patch. The take-home Pi image Deevnet publishes is in scope (v6).
- A local package mirror. It stays an evaluation candidate
  ([Substrate package mirror](/docs/platforms/evaluations/software/management-plane/package-mirror/));
  the cycle assumes internet access, as patching does today.
- Upgrades to a new line. Those are evaluated first, as Lifecycle Management's Upgrade stage requires,
  and go through their own change.

---

## Versions

### v1, know what runs (done 2026-11-23)

A dated report of what is actually running, compared with the catalog.

**Done when:**

- ✅ The catalog's rows are moved into a data file the page renders from, so a report can be
  compared with it mechanically. The page's grouping, columns and version-source terms stay as
  they are. {{< added "2026-11-22" >}}
- ✅ What was deployed as `-latest` is pinned: `deevnet-broker-account` (the `vernemq` role),
  `deevnet-log-user` (the `victorialogs` role), and the `deevnet-kit`, `deevnet-log-user` and
  `deevnet-log-bridge` binaries the Pi backend image fetches. The reference tenant's provider
  constraint moves to the line it actually runs. Each is pinned to the file `-latest` pointed at;
  the reference tenant had already moved to `~> 0.5`, locked at 0.5.0 {{< added "2026-11-22" >}}
- ✅ Every in-house repository is licensed: a LICENSE file in `deevnet-provisioning-api`,
  `terraform-provider-deevnet`, `deevnet-log-bridge`, `deevnet-container-image-factory` and the
  tenant repositories, and `galaxy.yml` agreeing with `LICENSE` in the `deevnet.mgmt` and
  `deevnet.net` collections. Every Deevnet repository is Apache-2.0 {{< added "2026-11-22" >}}
- ✅ **Core router collector:** `opnsense-version -v` for the release and base, and `pkg info` for
  the bundled packages in use (Kea, Unbound) and every installed `os-*` plugin. `opnsense-diag.sh`
  already gathers the first. {{< added "2026-11-22" >}}
- ✅ **Hypervisor collector:** `pveversion -v`, which covers Proxmox VE, the kernel, FRR and the
  SDN packages. {{< added "2026-11-22" >}}
- ✅ **Substrate service VM and Builder collector:** `/etc/os-release`, the kernel, the Podman
  version, and the image of every running container, read from the container and not from the
  unit file. {{< added "2026-11-22" >}}
- ✅ **Network device collector:** the switch's `show system-info`, and the controller and AP
  versions from the Omada Open API. {{< added "2026-11-22" >}}
- ✅ One dated report per run, kept on the Builder, listing for each item the observed version and
  the catalog's version, and for each running container the image its role pins, with every
  mismatch called out. {{< added "2026-11-23" >}}
- ✅ The report runs from one `make` target, and after any change record that upgrades something,
  so the catalog is updated in the same change. {{< added "2026-11-23" >}}

**The choices, the owner's, 2026-11-23.** The report has its own `make discover` target; [Build
Verification](/docs/roadmap/infrastructure/substrate/management-plane/) includes it when that report
is built, not before. The Pi lab is left out: its cards change with each experiment, so it has no
expected OS. Pins are compared for containers only: an OS or firmware has no pin to compare, only
its catalog row. Reports stay on the Builder, since the docs are public and a report lists the exact
version of everything the site runs.

**What the first runs found, 2026-11-23.** The core router had been updated by hand without a
record ([CHG-0081](/docs/changes/2026/0081-core-router-26-7-9/), which brought the
[Core Router Patch](/docs/runbook/substrate/lifecycle/core-router-patch/) procedure), and an unused
plugin the catalog didn't list. Automation could not log in to the switch at all: paramiko offered a
key file before the password, now turned off in each collection's `ansible.cfg`. The clean run read
15 systems with no mismatch and no pin drift. Podman still differs from VM to VM (5.8.4 to 5.8.9),
which v4's cycle evens out.

**Not in v1:** waiting updates (v2); release and advisory sources (v3); applying anything. Discovery
reports; changes go through change management.

### v2, told when an update is waiting (current)

Most of the substrate can say for itself that an update is waiting, so the operator is told at
login on the Builder rather than finding out. A watcher on the Builder asks every host once a day,
with credentials that can read and nothing else.

**Done when:**

- ✅ Every substrate service VM, Builder VM and hypervisor carries the read-only `deevnet-watch`
  account: no sudo, its key pinned to one program, `deevnet-watch-check` (its `updates` check),
  with `command=`, `restrict` and `from=` the Builder. The check reads the package manager's cache only (`dnf` on
  Fedora, `apt` on Proxmox VE), which each host's own timer keeps fresh, so it downloads nothing. {{< added "2026-11-23" >}}
- ✅ The watcher runs daily on the Builder as its own account. It asks every host, and compares
  OPNsense's published releases with the version the newest discovery report saw on the core
  router. {{< added "2026-11-23" >}}
- 🔄 It asks the Omada controller, with a view-only client, for the AP's latest firmware. Waits for
  the owner to make the client. {{< added "2026-11-24" >}}
- ✅ It writes its report on the Builder, in `/srv/updates`: everything waiting now, and a dated
  file of what was new. A banner in every interactive login shell shows what is new until the
  operator acknowledges it (`make update-watch-ack`). {{< added "2026-11-23" >}}
- ✅ What is new is reported once: a security update, a host newly behind, a new OPNsense release
  or device firmware. The banner counts the security updates. Ordinary package churn on a host
  already behind is listed but is not news. {{< added "2026-11-23" >}}
- ✅ Anything still waiting after 30 days is news again, and so is a system that didn't answer or
  couldn't check, once per outage. The hypervisors are listed but are not news, since Proxmox VE
  notifies its own (CHG-0079). {{< added "2026-11-23" >}}
- ✅ It is deployed by [CHG-0082](/docs/changes/2026/0082-update-watcher/), complete 2026-11-24
  after the timer's first run on its own. {{< added "2026-11-23" >}}

**The choices, the owner's, 2026-11-23.** The daily check runs unattended with credentials of its
own that can only read: the automation key, the vault and OpenBao stay with the operator's
sessions. The core router is watched upstream, not asked: OPNsense's only firmware privilege,
"System: Firmware", also allows installing updates and rebooting, so no key the watcher holds
reaches the router. Upstream watching sees point releases, not the package-only hotfixes between
them. **The report replaced mail the same day:** deploying CHG-0082 found the site's network
blocking outbound mail, and a mobile site's network changes under it, so the operator chose a
report on the Builder that needs no network at all.

**Not in v2:** the access switch, which the Omada controller does not manage and whose CLI cannot
say what is newer, and the Omada controller itself (both v3); a phone or ntfy alert, which waits
for operator alerting on the Observability item.

### v3, told when upstream moves on

What can't report its own updates is watched at the source: the container images (OpenBao,
VerneMQ, silo, Grafana, the VictoriaMetrics services, Alertmanager, ntfy), the Omada controller,
the access switch's firmware, and Deevnet's own pinned releases. The same report carries it.

**Done when:**

- ⏳ Each catalog item's **release source** and **advisory source** are recorded, as two new
  catalog columns. For OPNsense, one entry covers its bundled services too. {{< added "2026-11-22" >}}
- ⏳ The daily run checks every source (feeds where they exist, a checked list where they don't),
  with each source's last-seen release. {{< added "2026-11-23" >}}
- ⏳ A release newer than the running version is reported once, as in v2. {{< added "2026-11-23" >}}
- ⏳ Each new release is triaged as [Discovery](/docs/policies/lifecycle-management/discovery/)
  defines it (patch, new line, end of life, archived, advisory, or nothing relevant), and the outcome
  recorded, so nothing is triaged twice. {{< added "2026-11-22" >}}
- ⏳ End-of-life dates are recorded for the lines in use, and any within six months reported. {{< added "2026-11-22" >}}

**Not in v3:** response times by severity (v4 sets the cycle they are measured against).

### v4, apply on a cadence

Substrate hosts are patched within their approved line on a monthly cycle, in a fixed order, each
with a way back.

**Done when:**

- ⏳ The cycle is written in the runbook's [Patching](/docs/runbook/substrate/lifecycle/patching/)
  page: monthly, in the order substrate service VMs and the Builder, then the hypervisors one at a
  time, then the core router. A waiting security update the operator judges urgent starts an
  out-of-cycle run. {{< added "2026-11-22" >}}
- ⏳ A playbook patches the Fedora substrate service VMs and the Builder one host at a time:
  update, reboot when the kernel or a library in use changed, and a health check before the next
  host. A snapshot is taken before each, and kept until the next cycle. {{< added "2026-11-22" >}}
- ⏳ A runbook procedure patches each hypervisor within its Proxmox VE line, one at a time, with
  its VMs shut down or moved first and verified after. {{< added "2026-11-22" >}}
- ✅ A runbook procedure patches the core router within its OPNsense line: `make backup-router`
  before and after, and the previous release as the way back
  ([Core Router Patch](/docs/runbook/substrate/lifecycle/core-router-patch/), written after
  [CHG-0081](/docs/changes/2026/0081-core-router-26-7-9/)). {{< added "2026-11-22" >}}
- ⏳ A monthly cycle is one change record, of a pre-approved standard type defined in
  [Change Management](/docs/policies/change-management/), rather than a bespoke record per host. {{< added "2026-11-22" >}}
- ⏳ Each cycle ends with the v1 report run and the catalog updated from it. {{< added "2026-11-22" >}}
- ✅ Claude reads what needs patching through read-only MCP tools on the Builder, over the update
  and health watchers' reports, and a `patch-status` skill ranks it
  ([CHG-0089](/docs/changes/2026/0089-patch-tools-for-claude/)). {{< added "2026-11-24" >}}
- ⏳ Skills on those tools carry each kind of patch change: the monthly cycle over the playbook
  above, a Fedora release upgrade, and a hypervisor, each drafting its change record and verifying
  with the tools after. {{< added "2026-11-24" >}}

**Not in v4:** anything unattended (v5); switch and AP firmware, which stay per-change upgrades.

### v5, unattended where safe

Security updates go in without the operator where a failure cannot take the site down.

**Done when:**

- ⏳ Security-only automatic updates on the Fedora substrate service VMs, staggered so no two run
  at once, outside the hours the site is in use. {{< added "2026-11-22" >}}
- ⏳ Every unattended run is in the daily report; a failure or a pending reboot is told, not
  found. {{< added "2026-11-23" >}}
- ⏳ What is **never** patched unattended is written down, each with its reason: the hypervisors,
  the core router, switch and AP firmware, and OpenBao. {{< added "2026-11-22" >}}

### v6, shipped images stay current

The take-home images in the tenant downloads are rebuilt so they don't age.

**Done when:**

- ⏳ Every take-home image, the Pi's and each virtual machine format, is rebuilt with the monthly
  cycle, and after any security update affecting it, and passes its self-test before it is
  published. {{< added "2026-11-22" >}}
- ⏳ Each image states its base OS date, on the image and in the tenant downloads. {{< added "2026-11-22" >}}
- ⏳ The tenant guide says how an owner sees that a newer image exists, and how they update one
  already flashed. {{< added "2026-11-22" >}}

### Later

- Operator alerts by phone (ntfy) beside the report, once operator alerting is decided on the
  [Observability](/docs/roadmap/infrastructure/substrate/observability/) item
- Dependency and container image vulnerability scans before a release is staged
  ([Vulnerability Management](/docs/policies/risk-management/vulnerability-management/))
- Response times by severity, measured against the cycle
- A local package mirror, if the mirror evaluation is approved
