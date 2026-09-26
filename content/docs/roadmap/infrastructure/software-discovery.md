---
title: "Software Discovery"
weight: 7
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 12
---

# Software Discovery

Know what software is actually running, and hear about what upstream has released for it. This is
the [Discovery](/docs/policies/lifecycle-management/discovery/) stage of Lifecycle Management, built.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

The Software Catalog is the system of record for versions. Every other page links to it rather than
stating a version. Today it is assembled by reading inventory pins, role defaults, lockfiles and change
records, which leaves two gaps:
- **A pin is intent, not fact.** It says what the automation deploys, not what is running after a
  manual upgrade, a failed play or a host rebuilt by hand.
- **Much is never written down at all.** OPNsense's bundled packages, the FRR on the tenant
  hypervisor, Podman on the VMs, the OS on three of the four Pis and the Builder's own Fedora release
  are all "not recorded" in the catalog today.

A discovery run reads each system and produces a dated report of what it found, compared with the
catalog. The operator then updates the catalog from the report, or opens a change for the drift.

**In Scope**
- Read-only collection from every substrate system the Builder can reach, with the credentials
  automation already holds
- Versions only: licenses and support models stay hand-maintained in the catalog
- A comparison against the catalog and against the inventory pins

**Out of Scope**
- Upgrading anything. Discovery reports; changes go through change management.
- Tenant workloads. What a tenant runs is the tenant's to track.
- The travel router, which automation doesn't manage. It stays a manual entry.

---

## Catalog as data ⏳

- ⏳ Move the catalog's rows into a data file the page renders from, so a report can be compared
  with it mechanically. The page's grouping, columns and version-source terms stay as they are.

## Collectors ⏳

One collector per kind of system, each read-only:

- ⏳ **Core router:** `opnsense-version -v` for the release and base, and `pkg info` for the bundled
  packages in use (Kea, Unbound) and every installed `os-*` plugin. `opnsense-diag.sh` already
  gathers the first.
- ⏳ **Hypervisors:** `pveversion -v`, which covers Proxmox VE, the kernel, FRR and the SDN packages.
- ⏳ **Domain VMs and the Builder:** `/etc/os-release`, the kernel, the Podman version, and the image
  of every running container, read from the container and not from the unit file.
- ⏳ **Network devices:** the switch's `show system-info`, and the controller and AP versions from
  the Omada Open API.
- ⏳ **Raspberry Pis:** `/etc/os-release` and the kernel, for every Pi that answers. A Pi that
  doesn't answer is reported as unreachable, not skipped silently.

## Report and cadence ⏳

- ⏳ One dated report per run, listing for each item the observed version, the catalog's version and
  the inventory pin, with every mismatch called out.
- ⏳ Run it as part of [Build Verification](/docs/roadmap/infrastructure/mobile/management-plane/),
  and after any change record that upgrades something, so the catalog is updated in the same change.

## Release and advisory sources ⏳

The other half of discovery: hearing about new versions from the place that publishes them.

- ⏳ Record each catalog item's **release source** and **advisory source**, as two new catalog
  columns. For OPNsense, one entry covers its bundled services too.
- ⏳ Watch them: one place that gathers every source (feeds where they exist, a checked list where
  they don't), with each source's last-seen release.
- ⏳ Triage each new release as Discovery defines it (patch, new line, end of life, archived,
  advisory, or nothing relevant), and record the outcome, so nothing is triaged twice.
- ⏳ Record end-of-life dates for the lines in use, and surface any within six months.
