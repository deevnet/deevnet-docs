---
title: "Hypervisor Platform Uplift"
weight: 5
tasks_completed: 0
tasks_in_progress: 1
tasks_planned: 4
---

# Hypervisor Platform Uplift (Proxmox VE 8 → 9)

Move both hypervisors from Proxmox VE 8.4 to the 9.x series. This is a **prerequisite** for the
tenant fabric, not routine patching — PVE 9 is what makes the EVPN underlay manageable as code.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Both hypervisors currently run **PVE 8.4.1**. PVE 9 is based on Debian 13 (Trixie), so this is a
major-version distribution upgrade on each node, not a package update.

**In Scope**
- hv02 (tenant hypervisor, node `pve2`) — upgrade to PVE 9.x
- hv01 (management hypervisor, node `pve`) — upgrade to PVE 9.x
- Post-upgrade verification of the SDN API surface the tenant fabric depends on
- Alignment of the Terraform provider baseline with the upgraded platform

**Out of Scope**
- Building the tenant fabric itself — tracked in
  [Tenant Platform](/docs/roadmap/infrastructure/dvntm/tenant-platform/)
- Clustering either hypervisor — both remain standalone per
  [ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/)
- Ongoing patch strategy — tracked in
  [Patch Automation](/docs/roadmap/infrastructure/dvntm/patch-automation/)

---

## Why this blocks the tenant fabric

[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) build requirement #4 calls for
**a real underlay/VTEP identity now**, defined as code alongside the rest of the fabric, so that
adding a fabric member later is "add a neighbor" rather than "invent an underlay after the fact."

PVE 9 introduced **SDN Fabrics** — routed underlays (OpenFabric / OSPF) defined as first-class SDN
objects and driven through the API, expressly to serve as an EVPN underlay. PVE 8.4 has no such
object: verified against hv02, `GET /cluster/sdn/fabrics` returns *"Method not implemented"*.

On 8.4 the underlay would have to be a hand-maintained loopback in `/etc/network/interfaces` plus a
static `peers` list on the EVPN controller. That is precisely the node-local, hand-carried state
that requirements **#2 (SDN-as-code)** and **#4 (real underlay identity)** exist to prevent.

Upgrading first means the underlay is Terraform-managed from line one. hv02 currently holds no
tenant workloads, so this is the cheapest point in the project's life to do it.

---

## Pre-upgrade assessment 🔄

Establish what each node needs before either is touched.

- 🔄 Run `pve8to9 --full` on hv01 and hv02 and record the findings
- ⏳ Confirm both nodes are on the latest 8.4 point release first (an upgrade prerequisite)
- ⏳ Confirm root filesystem headroom (≥ 10 GB recommended) and a tested backup of every guest
- ⏳ Confirm out-of-band access to each node before starting — the upgrade drops network mid-run
- ⏳ Review breaking changes against the estate: cgroup v1 removal (old-systemd containers),
  `/etc/sysctl.conf` no longer honored (move to `/etc/sysctl.d/`), `/tmp` becomes tmpfs

## Uplift hv02 — tenant hypervisor ⏳

Do the tenant hypervisor first; it carries no tenant workloads yet, so the blast radius is smallest
and it is the node the fabric work is waiting on.

- Move repositories from Bookworm to Trixie and perform the distribution upgrade
- Verify the node returns healthy, guests start, and storage is intact
- Confirm `GET /cluster/sdn/fabrics` is now served

## Uplift hv01 — management hypervisor ⏳

The management plane runs here, so this node carries real workloads and needs a maintenance window.

- Inventory what runs on hv01 and what an outage affects before scheduling
- Same upgrade path; verify the management plane comes back whole

## Verify the fabric API surface ⏳

Confirm the platform now supports what the tenant fabric design assumes.

- SDN fabric objects (OpenFabric / OSPF) present and writable via the API
- EVPN controller, zone, VNet, subnet, and IPAM endpoints behave as expected on a **standalone**
  node — the fabric is self-contained per hypervisor, not cluster-scoped
- `frr` present on the tenant hypervisor; an EVPN zone will not come up without it

## Align the provisioning toolchain ⏳

- Re-baseline the `bpg/proxmox` Terraform provider pin against the upgraded platform. The provider's
  supported target is PVE 9.x; on 8.x it documents that functionality may be limited and that 8.x
  issues will not be addressed.
- Prefer the short-form `proxmox_sdn_*` resource names — the older
  `proxmox_virtual_environment_sdn_*` forms are deprecated and are removed at provider v1.0.

---

## Status

Assessment stage. No node has been upgraded. Tenant fabric implementation is intentionally held
behind this project so the underlay is never built as hand-maintained node state.
