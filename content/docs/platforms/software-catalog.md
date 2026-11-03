---
title: "Software Catalog"
weight: 6
---

# Software Catalog

Every piece of software the mobile site runs or is built with: the version in use, its license, and
who supports it. Grouped by substrate layer, like the rest of this section. Why each was chosen is on
its platform page or ADR; this page is the list.

**This page is the system of record for versions.** Other pages name the software and link here
instead of stating its version. They keep a version only where the context needs it:
- a change or incident record, which states what was true at the time
- a behavior tied to a version, such as "Grafana 13 cannot delete an organization"
- a minimum requirement, such as MicroPython 1.23 or later
- a literal value in a procedure, such as a firmware upgrade chain or an image tag

When a change upgrades something, it updates this page: its rows are kept in
`data/software_catalog.yaml`, where a report can compare them. Versions are gathered by hand today:
[Software Discovery](/docs/roadmap/infrastructure/substrate/software-discovery/) is the roadmap item for
scanning the site instead.

*As of 2026-09-26.*

---

## How to read this page

**Version source** says how the version is known:

| Source | Meaning |
|---|---|
| **Pin** | Declared in inventory, a role default, a lockfile or a Makefile. What the automation deploys. |
| **Observed** | Seen on the running system and written down, with the date and record. |
| **Bundled** | Ships inside another item's release and follows it. Its own version is not tracked separately. |
| **Not recorded** | Nothing in the repositories or the records says. Listed under [Gaps](#gaps). |

**Support** uses five terms:

| Support | Meaning |
|---|---|
| **Community** | Open source, with community support only. No vendor sells support for it. |
| **Community, commercial available** | Open source. The vendor sells support or a subscription, and Deevnet doesn't buy it. |
| **Vendor, no contract** | Proprietary, free of charge. The vendor ships updates; there is no support contract. |
| **Unmaintained** | Upstream no longer ships updates for what we run. |
| **In-house** | Deevnet's own. Supported by the operator. |

Third-party licenses are the upstream project's. In-house licenses are what the repository declares.

---

## Network

### Core router: OPNsense (`dv02cor002p01`)

{{< software-table "core-router" >}}

**Bundled services in use.** What the `deevnet.net` roles configure, taken from the OPNsense APIs they
call. Each follows the OPNsense release.

{{< software-table "core-router-services" >}}

**Plugins.**

{{< software-table "core-router-plugins" >}}

No other plugins are used. The collection has no plugin-install tasks.

### Switching, wireless and edge

{{< software-table "network-edge" >}}

---

## Management Plane

### Management hypervisor (`dv02hyp001p01`)

{{< software-table "management-hypervisor" >}}

### Substrate Service VMs

Every substrate service VM is **Fedora 44** from the template `fedora-server-44-1.7`, and runs its services as
Podman containers ([ADR-0013](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/)).
Image tags are pinned in the role defaults and mirrored on the Builder as tarballs.

{{< software-table "service-vms" >}}

### Builder (`dv00bld001p01`) and the provisioner VMs

{{< software-table "builder" >}}

---

## Tenant Compute

### Tenant hypervisor (`dv02hyp002p02`)

{{< software-table "tenant-hypervisor" >}}

### Raspberry Pi

{{< software-table "raspberry-pi" >}}

**The take-home `pi-backend` image** runs, as native binaries rather than containers:

{{< software-table "pi-backend" >}}

---

## Build and Automation Tooling

{{< software-table "build-tooling" >}}

---

## Tenant-Facing Tools

What the site hands a tenant developer, from the [tenant downloads](/docs/changes/2026/0025-tenant-downloads/).

{{< software-table "tenant-tools" >}}

---

## Deevnet's Own Software

What each piece does, where it runs and what it holds is in [Deevnet Software](/docs/platforms/deevnet-software/).

{{< software-table "deevnet-software" >}}

---

## Gaps

What this catalog could not settle, and what it found out of step. Each is a small follow-up.

**Versions that conflict or are missing:**
- **`dv02hyp001p01`'s Proxmox VE:** "8.4.1" on the platform page and roadmap, but "8.4.21" in
  [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) (2026-09-15). One is a typo.
- **OPNsense 25.7.10 to 26.7.3:** no change record covers the upgrade.
- **Not recorded** (each is a collector on the [Software Discovery](/docs/roadmap/infrastructure/substrate/software-discovery/) roadmap): the FreeBSD base, Kea and Unbound versions (all readable with `opnsense-version -v`
  and `pkg info`, which `opnsense-diag.sh` already collects); whether `os-wol` is installed; the
  GL.iNet firmware; the [ZimaBoard](/docs/platforms/hardware/network/zimaboard-832/)'s BIOS; the Pi bootloader EEPROMs; the `frr` package on `dv02hyp002p02`; Podman on the VMs and Builder; the Builder's
  Fedora release; the OS on `dv02rpi001p01` to `…003p01`.

**Unpinned:** ansible-core, Terraform and Packer on the Builder; `packer-builder-arm:latest`;
`tfplugindocs@latest`.

**Behind their source:** `deevnet-log-user` and `deevnet-broker-account` are pinned to v0.6.0 and
v0.5.1, the last builds staged, while the API they come from is at v0.15.0. The Pi's log bridge is an
untagged build.

**Unmaintained software still running:** MinIO (archived upstream; [ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/))
and Ubuntu 23.10 on `dv02rpi004p01` ([CHG-0027](/docs/changes/2026/0027-rpi004-switch-port/) follow-ups).

**Other pages that disagree with this one** (facts, not versions):
- The Proxmox ISO build still defaults to `PVE_ISO_VERSION=8.4-1`, while the tenant hypervisor runs 9.
- CHG-0018 says the hypervisors run Debian 12. `dv02hyp002p02` runs Debian 13.
