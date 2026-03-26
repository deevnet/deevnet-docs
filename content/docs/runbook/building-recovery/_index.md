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
| Capacity expansion | Adding hosts to existing site |

In all cases, the process starts with seeding MAC addresses into inventory.

---

## Stateless Substrate

The substrate (Core Router, hypervisors, network infrastructure) is stateless. All configuration is defined in source control and applied via automation. No backup, restore, or data recovery is required for the substrate itself—just rebuild from scratch.

This means:
- No substrate snapshots or backups to maintain
- No state synchronization concerns
- Any host can be wiped and rebuilt at any time
- Hardware replacement is straightforward

**Application tenants are different.** Tenant workloads may have stateful data (databases, user files, etc.) that requires backup and recovery procedures. See [Build Tenants](build-tenants/) for tenant-specific considerations.

---

## Greenfield Build Sequence

A complete build from scratch follows this sequence. Authority transitions and network segmentation are integrated steps — not separate procedures.

{{< mermaid >}}
flowchart TD
    A["<b>1. Stage Artifacts</b><br/>Fetch OS images, ISOs, SSH keys"]
    B["<b>2. Seed Inventory</b><br/>MAC addresses, host definitions"]
    C["<b>3. Vault Operations</b><br/>Decrypt secrets for automation"]
    D["<b>4. Configure PXE</b><br/><code>make bootstrap-auth</code>"]:::transition
    E["<b>5. Build Core Router</b><br/>Manual OPNsense USB install"]:::manual
    F["<b>6. Build Network</b><br/>VLANs, firewall, DHCP, wireless<br/><code>make core-auth</code>"]:::transition
    G["<b>7. Build Management Plane</b><br/>PXE boot Proxmox hypervisors"]
    H["<b>8. Verify Site</b><br/>Network, DNS, DHCP, PXE validation"]
    I["<b>9. Build Tenants</b><br/>Provision application VMs"]
    J["<b>10. Verify Tenants</b><br/>Application health checks"]

    A --> B --> C --> D --> E --> F --> G --> H --> I --> J

    classDef default fill:#2d333b,stroke:#539bf5,color:#adbac7
    classDef transition fill:#1a3a1a,stroke:#57ab5a,color:#8ddb8c
    classDef manual fill:#3d1f00,stroke:#d29922,color:#e6c068
{{< /mermaid >}}

**Legend:** {{< mermaid >}}flowchart LR; T["Authority transition"]:::transition; M["Manual step"]:::manual; classDef transition fill:#1a3a1a,stroke:#57ab5a,color:#8ddb8c; classDef manual fill:#3d1f00,stroke:#d29922,color:#e6c068{{< /mermaid >}}

---

## Build Procedures

### Preparation

- [Stage Artifacts](online-preparation/) — Fetch artifacts from internet sources
- [Seed Inventory](inventory-setup/) — Define MAC addresses and host definitions
- [Vault Operations](vault-operations/) — Decrypt secrets for automation

### Build

- [Configure PXE](build-sequence/) — Enter bootstrap-authoritative mode (`make bootstrap-auth`)
- [Build Network](build-network/) — Core Router install, network segmentation, transition to core-authoritative (`make core-auth`)
- [Build Management Plane](build-management-plane/) — PXE boot Proxmox hypervisors

### Validate

- [Verify Site](build-verification/) — Validate site infrastructure
- [Build Tenants](build-tenants/) — Provision application workloads
- [Verify Tenants](verify-tenants/) — Validate tenant applications

### Reference

- [Authority Transition](/docs/runbook/authority-transition/) — Standalone reference for DNS/DHCP authority transitions
- [Network Segmentation](/docs/runbook/network-migration/) — Detailed VLAN, firewall, and DHCP procedures

---

## Air-Gap Readiness

| Component | Method | Status |
|-----------|--------|--------|
| Proxmox VM template | kickstart + cdrom | Ready |
| Proxmox VE bare metal | embedded answer file | Ready |
| Fedora packages (install) | local mirror/ISO | Ready |
| Core Router | manual USB install | Manual — accepted prereq |

---

## Known Gaps

**Core Router** - No automated install exists, but this is an accepted manual prerequisite for the MVP. A fresh OPNsense install from USB is performed before the automated build begins, same as factory-resetting the switch and AP. Day-2 configuration is fully automated via the `deevnet.net` Ansible collection. Future options (pre-imaged NVMe, alternative whitebox solutions) are tracked under [Future Evaluations](../../platforms/evaluations/).

**Post-Install Updates** - See [Patching](../patching/) for day 2 considerations.
