---
title: "Extended Management Plane: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/management-plane/
  - /projects/management-plane/
weight: 3
tasks_completed: 7
tasks_in_progress: 4
tasks_planned: 4
---

# Extended Management Plane: Project Plan

Extended management services for the mobile site. Builds on the core substrate once it is operational. Its logging, telemetry and alerting are in the [Observability plan](/docs/roadmap/infrastructure/substrate/observability/plan/), and its secrets and identity in the [Secrets and Identity plan](/docs/roadmap/infrastructure/substrate/secrets-identity/plan/).

- **GitHub:** https://github.com/deevnet/ansible-collection-deevnet.mgmt
- **Documentation:** https://deevnet.github.io/deevnet-docs/

**Roadmap item:** [Extended Management Plane](/docs/roadmap/infrastructure/substrate/management-plane/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Deploy a unified management plane providing observability, security, and identity services for all substrate components, running as substrate service VMs on the management hypervisor.

**In Scope**
- Service selection, retention and alerting requirements
- Recovery copies of the network's configuration
- Build verification
- Ansible automation via `deevnet.mgmt` collection

**Out of Scope**
- Multi-site federation

---

## Requirements 🔄

- ✅ Define service selection criteria: each service's choice is its own ADR, weighing alternatives
  against the site's constraints (offline operation, memory, tenancy)
  ([ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) to
  [ADR-0027](/docs/architecture/decisions/platform-services/0027-tenant-log-store/))
- 🔄 Define retention policies (logs, metrics): logs have one retention period and a disk cap for
  the whole store ([ADR-0022](/docs/architecture/decisions/platform-services/0022-central-logging/) §6); metrics wait
  on ADR-0023
- 🔄 Define alerting channels and escalation: proposed in
  [ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/) (one Alertmanager to ntfy on
  Platform). Open: who watches the watcher, and reaching an off-site phone ([Management Plane → How the plane is watched](/docs/architecture/substrate/management-plane/#how-the-plane-is-watched))
- ✅ Define secrets access policies: every OpenBao client is an AppRole whose policy names exactly
  its paths ([ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/)); the image
  factory's is read-only ([CHG-0026](/docs/changes/2026/0026-build-secrets/))
- 🔄 Define identity/RBAC model: proposed in
  [ADR-0025](/docs/architecture/decisions/platform-services/0025-identity-directory/)

---

## Network Management ✅

Recovery copies of the network's own configuration. The core router and the Omada controller (on
`dv02nms001v01` since [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/)) are each backed up,
vault-encrypted, into the inventory at the end of every run that changes them, and on demand.

- ✅ Give the live controller a recovery path. Its settings are backed up after every change
  (`make wireless APPLY=1`, `make backup-wireless`), and a restore onto the Builder's cold controller
  was rehearsed in [CHG-0062](/docs/changes/2026/0062-device-backups-after-change/). The site is mostly
  built, so a backup follows each change rather than a timer
- ✅ Keep the core router's saved configurations somewhere that survives the Builder: they are what
  [Rebuild the Core Router](/docs/runbook/substrate/recovery/rebuild-core-router/) restores from,
  and they hold the router's secrets, so the copy is vault-encrypted. `make backup-router` seals it
  into the inventory with the vault password, where the ciphertext is public like every other vault
  file. A restore from the first backup was rehearsed in
  [CHG-0061](/docs/changes/2026/0061-core-router-restore-rehearsal/)

---

## Build Verification 🔄

Automated verification that the site was built according to inventory and is fully functional. Produces a single report proving build correctness.

- ⏳ Inventory conformance checks (running state matches inventory definitions)
- 🔄 Network connectivity matrix (verify all expected paths work): `segment-check.sh` proves what
  each SSID profile reaches and is refused, from a real client
  ([Segment Check](/docs/runbook/substrate/network/segment-check/)). Segments with no SSID aren't
  covered
- ⏳ Service health checks (DNS, DHCP, PXE, Proxmox API)
- ⏳ Hardware validation (MAC addresses, IP assignments match inventory)
- ⏳ Build report generation (consolidated pass/fail with evidence)

---

## Documentation ✅

- ✅ Management plane architecture overview, with how the layers depend on each other and how the
  plane is watched: [Management Plane](/docs/architecture/substrate/management-plane/)
- ✅ Service deployment runbook:
  [Build a Management-Hypervisor VM](/docs/runbook/substrate/building-recovery/build-management-hypervisor-vm/),
  with the domains and packaging in [Substrate Service VMs](/docs/platforms/management-plane/substrate-service-vms/)
- ✅ Operations and troubleshooting guide:
  [Troubleshoot a Service VM](/docs/runbook/substrate/recovery/service-vm-troubleshooting/)
