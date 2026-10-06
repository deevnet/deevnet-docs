---
title: "Building Infrastructure"
weight: 1
bookCollapseSection: true
aliases:
  - /docs/runbook/building-recovery/
---

# Building Infrastructure

Deevnet uses a two-phase model for substrate provisioning. These procedures apply whether building new infrastructure, recovering from failure, or replacing hardware.

---

## The Two-Phase Model

### Phase 1: Online Preparation

A builder node with internet access stages all required artifacts to the internal artifact server. This happens proactively—before any build or recovery.

**Staged artifacts include:** OS install trees, ISOs, container images, SSH keys.

### Phase 2: Offline Build

With artifacts pre-staged, the Builder can build the entire substrate without internet access. PXE boot pulls everything from local sources.

---

## When These Procedures Apply

| Scenario | Notes |
|----------|-------|
| Greenfield build | New infrastructure from scratch |
| Disaster recovery | Rebuild after failure |
| Hardware replacement | New hardware = new MAC addresses |
| Capacity expansion | Adding hosts to existing site |

In all cases, the process starts with seeding MAC addresses into inventory. Bare-metal
MACs are read off the hardware and recorded; management-hypervisor VMs have no NIC to read
until one is created, so their MACs are derived from the VMID instead — see
[Allocate VM Identity](vm-identity/).

---

## Stateless Substrate

The substrate (Core Router, hypervisors, network infrastructure) is stateless. All configuration is defined in source control and applied via automation. No backup, restore, or data recovery is required for the substrate itself—just rebuild from scratch.

This means:
- No substrate snapshots or backups to maintain
- No state synchronization concerns
- Any host can be wiped and rebuilt at any time, and the Builder and management-hypervisor VMs are, once per Fedora release ([Resiliency](/docs/policies/risk-management/resiliency/#rebuilds-are-exercised-on-a-schedule))
- Hardware replacement is straightforward

**Application tenants are different.** Tenant workloads may have stateful data (databases, user files, etc.) that requires backup and recovery procedures. A tenant rebuilds itself from its own repository and state; see [Tenant Operations](/docs/runbook/tenant/).

---

## Greenfield Build Sequence

**This is the site's one build order; other pages and records link here rather than restate it.** A complete build from scratch follows this sequence. Authority transitions and network segmentation are integrated steps — not separate procedures.

{{< mermaid >}}
flowchart TD
    Z["<b>0. Build the Builder</b><br/>Fedora by hand, then its own roles"]:::manual
    A["<b>1. Stage Artifacts</b><br/>Fetch OS images, ISOs, SSH keys"]
    B["<b>2. Seed Inventory</b><br/>MAC addresses, host definitions"]
    C["<b>3. Vault Operations</b><br/>Decrypt secrets for automation"]
    D["<b>4. Configure PXE</b><br/><code>make bootstrap-auth</code>"]:::transition
    E["<b>5. Build Core Router</b><br/>Manual OPNsense USB install"]:::manual
    F["<b>6. Build Network</b><br/>VLANs, firewall, DHCP, wireless<br/><code>make core-auth</code>"]:::transition
    G["<b>7. Build Hypervisors</b><br/>Manual Proxmox install, then Ansible"]:::manual
    H["<b>8. Allocate VM Identity</b><br/>VMID &rarr; MAC &rarr; DHCP reservation"]
    I["<b>9. Build Management-Hypervisor VMs</b><br/>Clone from template, or PXE netboot"]
    J["<b>10. Verify Site</b><br/>Network, DNS, DHCP, PXE validation"]
    K["<b>11. Admit Tenants</b><br/>Operator admits each tenant name"]
    L["<b>12. Tenants Apply</b><br/>Each tenant applies its own Terraform"]

    Z --> A --> B --> C --> D --> E --> F --> G --> H --> I --> J --> K --> L

    classDef default fill:#2d333b,stroke:#539bf5,color:#adbac7
    classDef transition fill:#1a3a1a,stroke:#57ab5a,color:#8ddb8c
    classDef manual fill:#3d1f00,stroke:#d29922,color:#e6c068
{{< /mermaid >}}

**Legend:** {{< mermaid >}}flowchart LR; T["Authority transition"]:::transition; M["Manual step"]:::manual; classDef transition fill:#1a3a1a,stroke:#57ab5a,color:#8ddb8c; classDef manual fill:#3d1f00,stroke:#d29922,color:#e6c068{{< /mermaid >}}

**Within step 9, the management-plane VMs come up in the order `deevnet.mgmt`'s `site.yml` runs
them:** all VMs first, then OpenBao, PowerDNS, the state store, the Deevnet API, the Omada
controller, the broker and log bridge, the log store, Grafana and the downloads site. The API's play
reads the messaging and observability VMs' SSH host keys, so those VMs must exist before it runs.
Certificates come from the Substrate CA through Ansible (`certs.yml`) and need nothing running
([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/)).

---

## Rebuild Tiers

**The site rebuilds in four tiers, each from the tiers below it.** A failure in one tier is
recovered by rebuilding it from the tiers beneath; what that takes is in
[Recovery](/docs/runbook/substrate/recovery/).

| Tier | What | Built from |
|---|---|---|
| **T0: the manual floor** | The steps below that a person does | People, by procedure |
| **T1: the substrate** | The Builder, the core router's configuration, the switch and AP, both hypervisors, the VM templates, the management-plane VMs, the tenant fabric | Inventory and ansible-vault |
| **T2: runtime services** | OpenBao, the Deevnet API and its database, PowerDNS, the state store, the broker, the log store, Grafana, the Omada controller | T1, seeded from ansible-vault |
| **T3: tenants** | Each tenant's networks, workloads, names, devices and applications | The tenant's repository, through the provider, and its own push |

**Some T2 services hold data nothing below them can recreate today:**
- OpenBao holds the Tenant Device CA's key, generated inside it, and its recovery key and Ansible
  login exist only in the vault once an initialization's output is locked in
  ([Vault Operations](vault-operations/)).
- The Deevnet API's database is the tenant registry, and the state store holds tenants' Terraform
  state, which carries their device secrets. Both are on the provisioning VM's OS disk, with no copy.
- The Omada controller holds tenants' Wi-Fi keys, and the broker's database their device accounts.

The [2026-10 Rebuild and Access review](/docs/architecture/reviews/2026-10-rebuild-and-access/)
tracks closing each of these.

### The manual floor

**These steps are done by a person on every full build, and the automation starts where they end:**

| Step | Where it is |
|---|---|
| Install Fedora on the Builder from USB | [Build the Builder](build-the-builder/) |
| Choose and hold the vault password | [Vault Operations](vault-operations/) |
| Install OPNsense from USB, set its interface addresses and `next_server`, create its API key | [Build Network](build-network/), [Rebuild the Core Router](/docs/runbook/substrate/recovery/rebuild-core-router/) |
| Factory-reset the switch and the AP | [Build Network](build-network/) |
| Install Proxmox from the ISO, run its console bootstrap, issue its API tokens | [Build a Hypervisor](build-hypervisor/) |
| Put the Fedora ISO into the hypervisor's `local:iso` before a template build | Not yet in a runbook: the template build expects it there (`deevnet-image-factory/packer/proxmox/fedora-base-image/fedora.pkr.hcl`, `iso_download_pve`), and a reinstall wipes it |
| Run the Omada setup wizard, create the Owner and the Open API clients | ADR-0009 §5 |
| Generate OpenBao's seal key; lock in an initialization's output | [Vault Operations](vault-operations/) |
| The Root, Site and issuing CA ceremonies | [Root of Trust](/docs/runbook/root-of-trust/) |

---

## Build Procedures

### Preparation

- [Build the Builder](build-the-builder/) — Make the Ansible control node from a bare machine
- [Stage Artifacts](online-preparation/) — Fetch artifacts from internet sources
- [Seed Inventory](inventory-setup/) — Define MAC addresses and host definitions
- [Vault Operations](vault-operations/) — Decrypt secrets for automation
- [Build-Time Secrets](build-secrets/) — How Packer and the fabric's Terraform get the Proxmox token, and how to rotate it

### Build

- [Configure PXE](build-sequence/) — Enter bootstrap-authoritative mode (`make bootstrap-auth`)
- [Build Network](build-network/) — Core Router install, network segmentation, transition to core-authoritative (`make core-auth`)
- [Build a Hypervisor](build-hypervisor/) — Install and configure the Proxmox hypervisors
- [Allocate VM Identity](vm-identity/) — Derive management-VM MACs from their VMID before first boot
- [Build a Management-Hypervisor VM](build-management-hypervisor-vm/) — Put an OS on the VM, by template clone or PXE netboot

### Validate

- [Verify Site](build-verification/) — Validate site infrastructure
- [Tenant Admission](/docs/runbook/substrate/tenant-admission/) — Admit each tenant name; each tenant then applies its own Terraform ([Tenant Operations](/docs/runbook/tenant/))

### Reference

- [Authority Transition](/docs/runbook/substrate/building-recovery/authority-transition/) — Standalone reference for DNS/DHCP authority transitions
- [Repave the Builder](repave-builder/) — Reinstall the hardware Builder from a temporary builder VM, over PXE, while the Builder is still there to help
- [CHG-0001: Flat Network → VLANs](/docs/changes/2026/0001-flat-network-to-vlans/) — the VLAN, firewall and DHCP procedure, as recorded when the mobile site was segmented

---

## Air-Gap Readiness

| Component | Method | Status |
|-----------|--------|--------|
| Proxmox VM template | kickstart + cdrom | Ready |
| Proxmox VE bare metal | manual install from the staged ISO | Manual |
| Fedora packages (install) | local mirror/ISO | Ready |
| Core Router | manual USB install | Manual — accepted prereq |

---

## Known Gaps

**Core Router** - No automated install exists, but this is an accepted manual prerequisite for the MVP. A fresh OPNsense install from USB is performed before the automated build begins, same as factory-resetting the switch and AP. Day-2 configuration is fully automated via the `deevnet.net` Ansible collection. Future options (pre-imaged NVMe, alternative whitebox solutions) are tracked under [Evaluations](/docs/platforms/evaluations/).

**Hypervisors** - Proxmox VE is installed by hand from the ISO staged on the artifact server. An unattended ISO with an embedded answer file exists in `deevnet-image-factory` but is unfinished and has not installed either node; it is on the [Builder roadmap](/docs/roadmap/infrastructure/mobile/builder/).

**Post-Install Updates** - See [Patching](/docs/runbook/substrate/lifecycle/patching/) for day 2 considerations.
