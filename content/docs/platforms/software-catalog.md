---
title: "Software Catalog"
weight: 6
---

# Software Catalog

Every piece of software the mobile site runs or is built with: the version in use, its license, and
who supports it. Grouped by substrate layer, like the rest of this section. Why each was chosen is on
its platform page or ADR; this page is the list.

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

| Component | Version | License | Support | Version source |
|---|---|---|---|---|
| **OPNsense** | **26.7.3_11** | BSD-2-Clause | Community, commercial available (Deciso) | Observed 2026-09-19 ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)) and 2026-09-21 ([INC-0004](/docs/incidents/2026/0004-core-router-lost/)) |
| FreeBSD base | not recorded | BSD-2-Clause | Bundled | Bundled with OPNsense |

**Bundled services in use.** What the `deevnet.net` roles configure, taken from the OPNsense APIs they
call. Each follows the OPNsense release.

| Service | Used for | License | Configured by |
|---|---|---|---|
| **Kea DHCPv4** | DHCP on every segment, and static reservations. ISC dhcpd and dnsmasq are not used on the router. | MPL-2.0 | `opnsense_dhcp` (`/api/kea/…`) |
| **Unbound** | The site resolver: host overrides, aliases, and forwarding of tenant zones to PowerDNS | BSD-3-Clause | `opnsense_dns` (`/api/unbound/…`) |
| **pf** (through the OPNsense filter and alias APIs) | Zone policy, and the `deevnet_private` alias | BSD | `opnsense_firewall` (`/api/firewall/…`) |
| VLAN interfaces | One per segment, on `re0` | BSD-2-Clause | `opnsense_vlans` (`/api/interfaces/…`) |
| Gateways and static routes | The tenant fabric route `10.20.128.0/18` | BSD-2-Clause | `opnsense_routes` (`/api/routing/…`, `/api/routes/…`) |
| Configuration backup | Pre-change backups | BSD-2-Clause | Migration playbooks (`/api/core/backup/…`) |

**Plugins.**

| Plugin | State | License | Notes |
|---|---|---|---|
| `os-wol` | Required, but whether it is installed is not recorded | BSD-2-Clause | Wake-on-LAN for the Builder and both hypervisors (`opnsense_wol`) |
| `os-realtek-re` | Proposed, not installed | BSD-2-Clause | Vendor NIC driver: an open corrective action on [INC-0004](/docs/incidents/2026/0004-core-router-lost/) |

No other plugins are used. The collection has no plugin-install tasks.

### Switching, wireless and edge

| Component | Where | Version | License | Support | Version source |
|---|---|---|---|---|---|
| **TP-Link SG2218 firmware** | Access switch `dv02acc001p01` (hardware 1.20) | **1.20.24** Build 20260509; 1.20.1 kept in the other image slot | Proprietary | Vendor, no contract | Observed 2026-09-16 ([CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/)) |
| **TP-Link EAP650-Outdoor firmware** | AP `dv02wap001p01` (v1.0) | **1.3.11** Build 20260703 | Proprietary | Vendor, no contract | Observed 2026-09-15 ([CHG-0005](/docs/changes/2026/0005-wireless-ap-firmware-and-adoption/)) |
| **Omada Software Controller** | Container on `dv02nms001v01`; cold spare on the Builder | **6.3.0.45** | Proprietary, free of charge | Vendor, no contract | Pin (`omada_image_tag`); observed 2026-09-15 ([CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/)) |
| Omada container image | As above | `mbentley/omada-controller:6.3.0.45` | Community packaging of the vendor's software | Community | Pin. Fallbacks 6.2.14.11 and 6.1 are mirrored |
| **GL.iNet firmware** | Travel router `dv02edg001p01` (GL-AXT1800) | not recorded. The platform page says "OpenWrt 23.05-SNAPSHOT", undated | OpenWrt base GPL-2.0; GL.iNet additions proprietary | Vendor, no contract | Not recorded. Not managed by automation |

---

## Management Plane

### Management hypervisor (`dv02hyp001p01`)

| Component | Version | License | Support | Version source |
|---|---|---|---|---|
| **Proxmox VE** | **8.4.1** (see [Gaps](#gaps)) | AGPL-3.0 | Community, commercial available. The nodes use the **no-subscription** repository | Observed, undated (platform page, roadmap) |
| Debian | 12 (Bookworm) | Free software, per package | Community | Bundled with Proxmox VE 8 |
| Linux kernel | 6.8.12 | GPL-2.0 | Bundled | Observed 2026-09-15 ([CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/)) |

### Domain VMs

Every domain VM is **Fedora 44** from the template `fedora-server-44-1.7`, and runs its services as
Podman containers ([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/)).
Image tags are pinned in the role defaults and mirrored on the Builder as tarballs.

| Component | VM | Version | License | Support | Version source |
|---|---|---|---|---|---|
| **Fedora Server** | all | **44** (template build 1.7). Kernel 7.2.5, systemd 259 | Free software, per package (Fedora Project) | Community | Pin (`deevnet_fedora_current`); observed 2026-09-15/21 |
| Podman | all | not recorded (the Fedora 44 package) | Apache-2.0 | Community | Not recorded |
| **OpenBao** | `dv02idn001v01` | **2.6.2** | MPL-2.0 | Community (Linux Foundation project) | Pin; staged 2026-09-17 ([CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/)) |
| **PowerDNS Authoritative** | `dv02idn001v01` | **4.9.17** | GPL-2.0 | Community, commercial available (PowerDNS) | Pin |
| **Deevnet API** | `dv02prv001v01` | **v0.8.0** | No license file | In-house | Pin; deployed 2026-09-24 ([CHG-0024](/docs/changes/2026/0024-tenant-dashboards/)) |
| **PostgreSQL** | `dv02prv001v01` (the API), `dv02msg001v01` (VerneMQ auth) | **17.11** | PostgreSQL License | Community | Pin |
| **MinIO** | `dv02prv001v01` (Terraform state) | **RELEASE.2025-09-07T16-13-09Z** | AGPL-3.0 | **Unmaintained.** The community edition was archived 2026-04-25, and the tag can no longer be pulled | Pin. Replacement decided in [ADR-0026](/docs/architecture/decisions/0026-object-storage/) |
| **Omada Software Controller** | `dv02nms001v01` | 6.3.0.45 | See [Network](#switching-wireless-and-edge) | | |
| **VerneMQ** | `dv02msg001v01` | **2.2.0**, built from source | Apache-2.0 (source). Upstream binaries carry an EULA, which is why it is built here | Community, commercial available (Octavo Labs) | Pin; observed 2026-09-20 ([CHG-0015](/docs/changes/2026/0015-vernemq-broker/)) |
| **MQTT log bridge** | `dv02msg001v01` | **v0.1.1** | not checked (its repository isn't in this workspace) | In-house | Pin; deployed 2026-09-22 ([CHG-0021](/docs/changes/2026/0021-mqtt-log-bridge/)) |
| **VictoriaLogs** | `dv02obs001v01` | **v1.52.0** | Apache-2.0 | Community, commercial available (VictoriaMetrics) | Pin; observed 2026-09-21 ([CHG-0018](/docs/changes/2026/0018-central-log-store/)) |
| **vmauth** | `dv02obs001v01` | **v1.152.0** | Apache-2.0 | Community, commercial available (VictoriaMetrics) | Pin; observed 2026-09-21 |
| **Grafana OSS** | `dv02obs001v01` | **13.2.2** | AGPL-3.0 | Community, commercial available (Grafana Labs) | Pin; deployed 2026-09-24 ([CHG-0024](/docs/changes/2026/0024-tenant-dashboards/)) |
| victoriametrics-logs-datasource plugin | `dv02obs001v01` | **0.32.0** | not checked | Community, commercial available (VictoriaMetrics) | Pin; observed 2026-09-24 |
| **nginx** (tenant downloads) | `dv02obs001v01` | **1.29.1-alpine** | BSD-2-Clause | Community, commercial available (F5) | Pin; deployed 2026-09-24 ([CHG-0025](/docs/changes/2026/0025-tenant-downloads/)) |
| `deevnet-log-user` | `dv02obs001v01` | Built from the API's tag; deployed as `-latest` | No license file | In-house | Not pinned |
| (collector) | `dv02col001v01` | Built empty. vmagent is proposed in [ADR-0023](/docs/architecture/decisions/0023-metrics-and-alerting/) | | | |

### Builder (`dv00bld001p01`) and the provisioner VMs

| Component | Version | License | Support | Version source |
|---|---|---|---|---|
| Fedora Workstation (Builder) | "43 or later". The exact release is not recorded | Free software, per package | Community | Not recorded |
| Fedora Server (`dv02bld001v01`, `dv02bld002v01`) | 44 | Free software, per package | Community | Pin |
| nginx (artifact server) | Fedora package | BSD-2-Clause | Community | Not pinned |
| tftp-server, syslinux, grub2 (PXE) | Fedora packages | BSD / GPL-2.0 / GPL-3.0 | Community | Not pinned |
| dnsmasq | Fedora package; installed but disabled | GPL-2.0 | Community | Not pinned |

---

## Tenant Compute

### Tenant hypervisor (`dv02hyp002p02`)

| Component | Version | License | Support | Version source |
|---|---|---|---|---|
| **Proxmox VE** | **9.2.11** | AGPL-3.0 | Community, commercial available. No-subscription repository | Observed 2026-08-30 ([Hypervisor Uplift](/docs/roadmap/infrastructure/mobile/hypervisor-uplift/)) |
| Debian | 13 (Trixie) | Free software, per package | Community | Bundled with Proxmox VE 9 |
| Proxmox SDN (`libpve-network-perl`) | 1.6.7 | AGPL-3.0 | Bundled | Observed 2026-08-30 |
| **FRR** (EVPN, OpenFabric underlay) | not recorded. `frr-pythontools` is 10.6.1-1+pve3 | GPL-2.0-or-later | Community | Observed 2026-08-30 (pythontools only) |
| Tenant egress agent | follows `deevnet.net` 1.0.0 | Apache-2.0 (collection `LICENSE`) | In-house | Not versioned |

### Raspberry Pi

| Component | Where | Version | License | Support | Version source |
|---|---|---|---|---|---|
| **Ubuntu** | `dv02rpi004p01` | **23.10** | Free software, per package | **Unmaintained** (end of life) | Observed 2026-09-25 ([CHG-0027](/docs/changes/2026/0027-rpi004-switch-port/)) |
| (OS) | `dv02rpi001p01`, `…002p01`, `…003p01` | not recorded | | | Not recorded |
| **Raspberry Pi OS Lite** (arm64) | Base of the image-factory Pi builds and the take-home `pi-backend` image | **Bookworm, 2025-11-24**. Trixie 2025-11-24 is mirrored but unused | Free software, with some proprietary firmware | Community (Raspberry Pi Ltd) | Pin |

**The take-home `pi-backend` image** runs, as native binaries rather than containers:

| Component | Version | License | Version source |
|---|---|---|---|
| VictoriaLogs | v1.52.0 | Apache-2.0 | Pin |
| vmauth (vmutils) | v1.152.0 | Apache-2.0 | Pin |
| Grafana OSS | 13.2.2 | AGPL-3.0 | Pin (sha256) |
| victoriametrics-logs-datasource | 0.32.0 | not checked | Pin |
| `deevnet-kit` | the API's tag | No license file | Built from the API repository |
| `deevnet-log-bridge` | `-latest` | not checked | Not pinned |
| Mosquitto, Podman | Bookworm packages (Podman 4.3) | EPL-2.0 / EDL-1.0; Apache-2.0 | Not pinned |

---

## Build and Automation Tooling

| Component | Version | License | Support | Version source |
|---|---|---|---|---|
| **ansible-core** | not pinned. Collections require `>=2.14` | GPL-3.0 | Community, commercial available (Red Hat) | Not pinned |
| `ansible.posix` | `>=1.5.0` | GPL-3.0 | Community | Pin (constraint) |
| `community.general` | `>=8.0.0` | GPL-3.0 | Community | Pin (constraint). `deevnet.builder` uses it without declaring it |
| `ansible.netcommon` | `>=7.0.0` | GPL-3.0 | Community | Pin (constraint) |
| paramiko, proxmoxer, requests | paramiko `>=2.12.0`; others not pinned | LGPL-2.1; MIT; Apache-2.0 | Community | Partly pinned |
| **Terraform** (Builder, fabric) | not pinned. Configurations require `>= 1.5`; fabric state written by 1.14.3 | BUSL-1.1 | Vendor (HashiCorp), no contract | Not pinned |
| Terraform (handed to tenants) | **1.16.4** | BUSL-1.1 | Vendor (HashiCorp), no contract | Pin (tenant downloads) |
| `bpg/proxmox` provider | `~> 0.101`, locked **0.111.1** | MPL-2.0 | Community | Pin (lockfile) |
| `grafana/grafana` provider | **4.46.0** | MPL-2.0 | Community, commercial available (Grafana Labs) | Pin (tenant downloads) |
| **Packer** | not pinned | BUSL-1.1 | Vendor (HashiCorp), no contract | Not pinned |
| `hashicorp/proxmox` Packer plugin | `~> 1` | MPL-2.0 | Community | Pin (constraint) |
| `packer-builder-arm` (Pi builds) | `:latest` container | Apache-2.0 | Community | Not pinned |
| **Go** | API `go 1.25.0`, built with 1.25.9; provider `go 1.25.5` | BSD-3-Clause | Community | Pin |
| terraform-plugin-framework | v1.15.1 | MPL-2.0 | Community (HashiCorp) | Pin (`go.mod`) |
| GoReleaser | v2 | MIT | Community, commercial available | Pin (major only) |
| **Hugo** (extended) | **0.140.1** | Apache-2.0 | Community | Pin (CI workflow, Builder) |
| hugo-book theme | v11.0.0-1-g24d3465 | MIT | Community | Pin (submodule commit) |
| GitHub Actions | checkout v4, configure-pages v5, upload-pages-artifact v3, deploy-pages v4 | MIT | Vendor (GitHub) | Pin (major only) |

---

## Tenant-Facing Tools

What the site hands a tenant developer, from the [tenant downloads](/docs/changes/2026/0025-tenant-downloads/).

| Component | Version | License | Support | Version source |
|---|---|---|---|---|
| **`deevnet/deevnet` provider** | **v0.4.1** | No license file | In-house | Pin (tenant downloads); tag |
| `install-provider.sh`, `tenant-check.sh` | ship with the provider | No license file | In-house | Follow the provider tag |
| Terraform | 1.16.4 | BUSL-1.1 | Vendor, no contract | Pin |
| `grafana/grafana` provider | 4.46.0 | MPL-2.0 | Community, commercial available | Pin |
| MicroPython (Pico W) | 1.29.0 | MIT | Community | Pin |
| Raspberry Pi Imager | 2.0.11.1 | Apache-2.0 | Community (Raspberry Pi Ltd) | Pin |
| Arduino IDE, ESP32 board package, PubSubClient | not recorded | LGPL/GPL; LGPL-2.1; MIT | Community | Not recorded |

---

## Deevnet's Own Software

| Repository | Version | License | What it builds |
|---|---|---|---|
| `deevnet-provisioning-api` | tag **v0.8.1**, deployed **v0.8.0** | **No license file** | The API, `deevnet-broker-account`, `deevnet-log-user`, `deevnet-kit` (all share its tag) |
| `terraform-provider-deevnet` | tag **v0.4.1** | **No license file** | The provider, `install-provider.sh`, `tenant-check.sh` |
| `deevnet-log-bridge` | **v0.1.1** deployed | not checked | The MQTT log bridge |
| `ansible-collection-deevnet.builder` | 1.0.0, no tags | MIT | Builder, artifact server, PXE roles |
| `ansible-collection-deevnet.mgmt` | 1.0.0, no tags | **`galaxy.yml` says MIT; `LICENSE` is Apache-2.0** | Management-plane roles |
| `ansible-collection-deevnet.net` | 1.0.0, no tags | **`galaxy.yml` says MIT; `LICENSE` is Apache-2.0** | Network roles, `segment-check.sh`, `opnsense-diag.sh`, the tenant egress agent |
| `ansible-inventory-deevnet` | no tags | MIT | Inventory |
| `deevnet-image-factory` | no tags | Apache-2.0 | Packer and Pi images |
| `deevnet-tenant-fabric` | tags `tenant-module-v1.1.0` and earlier | not checked | Tenant fabric SDN (Terraform) |
| `deevnet-docs` | no tags | Apache-2.0 | This site |

---

## Gaps

What this catalog could not settle, and what it found out of step. Each is a small follow-up.

**Versions that conflict or are missing:**
- **`dv02hyp001p01`'s Proxmox VE:** "8.4.1" on the platform page and roadmap, but "8.4.21" in
  [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) (2026-09-15). One is a typo.
- **OPNsense 25.7.10 to 26.7.3:** no change record covers the upgrade.
- **Not recorded:** the FreeBSD base, Kea and Unbound versions (all readable with `opnsense-version -v`
  and `pkg info`, which `opnsense-diag.sh` already collects); whether `os-wol` is installed; the
  GL.iNet firmware; the `frr` package on `dv02hyp002p02`; Podman on the VMs and Builder; the Builder's
  Fedora release; the OS on `dv02rpi001p01` to `…003p01`.

**Unpinned:** ansible-core, Terraform and Packer on the Builder; `packer-builder-arm:latest`;
`tfplugindocs@latest`; `deevnet-log-user` and `deevnet-log-bridge` deployed as `-latest`; tdemo's
`deevnet/deevnet ~> 0.1` against an actual 0.4.x.

**Licenses:** `deevnet.mgmt` and `deevnet.net` declare MIT in `galaxy.yml` and ship an Apache-2.0
`LICENSE`. The API, the provider and the tenant repositories have no license file.

**Unmaintained software still running:** MinIO (archived upstream; [ADR-0026](/docs/architecture/decisions/0026-object-storage/))
and Ubuntu 23.10 on `dv02rpi004p01` ([CHG-0027](/docs/changes/2026/0027-rpi004-switch-port/) follow-ups).

**Other pages that disagree with this one:**
- [Core Router](/docs/platforms/network/core-router/): OPNsense "24.x".
- [Network Controllers](/docs/platforms/network/network-controllers/): the controller "on the
  bootstrap node". It moved to `dv02nms001v01` in CHG-0008.
- [Access Switch](/docs/platforms/network/access-switch/): managed by "Omada API". It is standalone,
  configured over CLI, and its adoption ([CHG-0009](/docs/changes/2026/0009-access-switch-adoption/))
  is on hold.
- [Change Management](/docs/policies/change-management/): controller "6.1".
- The PXE role page's example shows Fedora 43, and the Proxmox ISO build still defaults to 8.4-1.
- CHG-0018 says the hypervisors run Debian 12. `dv02hyp002p02` runs Debian 13.
