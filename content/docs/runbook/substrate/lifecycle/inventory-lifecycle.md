---
title: "Inventory Lifecycle"
weight: 2
aliases:
  - /docs/runbook/lifecycle/inventory-lifecycle/
  - /docs/runbook/inventory-lifecycle/
---

# Inventory & Lifecycle Management

Documents how **infrastructure assets are tracked, managed, and retired**.

---

## Scope

This section includes:

- Host identity and inventory sources of truth
- Hardware lifecycle stages (active, standby, retired)
- Image and configuration lifecycle expectations
- Decommissioning and cleanup principles

This section ensures infrastructure ages intentionally, not accidentally.

---

## Lifecycle Stages

| Stage | Description |
|-------|-------------|
| **Provisioning** | Host being set up, not yet in service |
| **Active** | In production use |
| **Standby** | Available but not currently assigned |
| **Maintenance** | Temporarily offline for updates/repairs |
| **Retired** | Decommissioned, removed from inventory |

---

## Inactive hosts

**A host that is declared in inventory but not built is in the `inactive` group, and in no other.**
No play builds or configures it, and the router's DNS and DHCP roles give it no record and no
reservation, deleting any they made before. Its `host_vars` and its identity stay: a VM keeps its
VMID and MAC, reserved, and so its address. Making it active brings it back exactly as it was.

| Host | What it is | Active in | Inactive since |
|---|---|---|---|
| `dv02bld001v01` | The temporary builder, cloned from the template, that [repaves the Builder](/docs/runbook/substrate/building-recovery/repave-builder/) | `control_plane`, `management_plane`, `builder`, `workstations`, `artifact_servers`, `bootstrap_nodes` | [CHG-0088](/docs/changes/2026/0088-builder-vms-inactive/) |
| `dv02bld002v01` | The UEFI PXE install test target. Its per-MAC GRUB config stays on the Builder | `control_plane`, `management_plane`, `builder` | [CHG-0088](/docs/changes/2026/0088-builder-vms-inactive/) |

**Making a host inactive is a change record.** In inventory, move the host out of every group into
`inactive`, with a comment listing the groups it leaves, and take its address out of any allow list
(OpenBao's AppRole CIDRs). Move its service CNAMEs to another host first: the DNS role deletes the
host's own record, not aliases pointing at it. Then:

1. Run the watchers' roles on the Builder (`make update-watch`, `make health-watch` in
   `deevnet.builder`), so they stop asking it.
2. Shut it down and destroy it, with its disks (`qm destroy <vmid> --purge` on its hypervisor).
3. Run `make dns` and `make dhcp` in `deevnet.net`: its record and reservation are deleted.
4. Remove it from the Builder's `known_hosts` (`ssh-keygen -R`), the operator's and `deevnet-watch`'s.

**Making a host active is the reverse.** Move it back into the groups its comment lists and out of
`inactive`, put its address back in any allow list it left, and run `make dns` and `make dhcp` so its
reservation is there before it first boots. Then build it as it was built: a template clone through
`deevnet.mgmt`'s `site.yml`, or a PXE install, then its own roles.

---

## Inventory Sources of Truth

- **ansible-inventory-deevnet** - Canonical host identity
- **OPNsense** - Authoritative DNS/DHCP (production)
- **Builder** - Authoritative DNS/DHCP (during provisioning)

---

## Decommissioning

When retiring a host:

1. Remove from active service (update DNS CNAMEs)
2. Run cleanup playbook (remove secrets, keys)
3. Update inventory status to retired
4. Archive or wipe storage as appropriate
5. Update documentation

