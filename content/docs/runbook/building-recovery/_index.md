---
title: "Building Infrastructure"
weight: 1
bookCollapseSection: true
---

# Building Infrastructure

Deevnet uses a two-phase model for substrate provisioning. These procedures apply whether building new infrastructure, recovering from failure, or replacing hardware.

---

## The Two-Phase Model

### Phase 1: Online Preparation

A builder node with internet access stages all required artifacts to the internal artifact server. This happens proactively—before any build or recovery.

**Staged artifacts include:** OS install trees, ISOs, container images, SSH keys.

### Phase 2: Offline Build

With artifacts pre-staged, the bootstrap node can build the entire substrate without internet access. PXE boot pulls everything from local sources.

---

## When These Procedures Apply

| Scenario | Notes |
|----------|-------|
| Greenfield build | New infrastructure from scratch |
| Disaster recovery | Rebuild after failure |
| Hardware replacement | New hardware = new MAC addresses |
| Capacity expansion | Adding hosts to existing substrate |

In all cases, the process starts with seeding MAC addresses into inventory.

---

## Stateless Substrate

The substrate (Core Router, hypervisors, network infrastructure) is stateless. All configuration is defined in source control and applied via Ansible. No backup, restore, or data recovery is required for the substrate itself—just rebuild from scratch.

This means:
- No substrate snapshots or backups to maintain
- No state synchronization concerns
- Any host can be wiped and rebuilt at any time
- Hardware replacement is straightforward

**Application tenants are different.** Tenant workloads may have stateful data (databases, user files, etc.) that requires backup and recovery procedures. See [Build Tenants](build-tenants/) for tenant-specific considerations.

---

## Build Procedures

- [Stage Artifacts](online-preparation/) — Fetch artifacts from internet sources
- [Seed Inventory](inventory-setup/) — Define MAC addresses and host definitions
- [Configure PXE](build-sequence/) — Set PXE authority for build scenario
- [Build Network](build-network/) — Core Router, VLANs, wireless
- [Build Management Plane](build-management-plane/) — Proxmox hypervisors
- [Verify Substrate](build-verification/) — Validate substrate infrastructure
- [Build Tenants](build-tenants/) — Provision application workloads
- [Verify Tenants](verify-tenants/) — Validate tenant applications

---

## Air-Gap Readiness

| Component | Method | Status |
|-----------|--------|--------|
| Proxmox VM template | kickstart + cdrom | Ready |
| Proxmox VE bare metal | embedded answer file | Ready |
| Fedora packages (install) | local mirror/ISO | Ready |
| Core Router | manual | Gap |

---

## Known Gaps

**Core Router** - No automated install. Current workaround is manual install from USB followed by config restore via API. Future options include USB installer with embedded config or alternative whitebox solution.

**Post-Install Updates** - See [Patching](../patching/) for day 2 considerations.
