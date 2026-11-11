---
title: "Extended Management Plane: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/management-plane/
  - /projects/management-plane/
weight: 3
tasks_completed: 5
tasks_in_progress: 6
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

## Network Management ⏳

Recovery copies of the network's own configuration. The Omada controller runs on `dv02nms001v01`
since [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/). Its data has one snapshot, taken by
hand on 2026-10-06, with a copy on the Builder.
The core router's `config.xml` is backed up vault-encrypted into the inventory by `make backup-router`
and before every firewall apply.

- 🔄 Give the live controller a recovery path. One snapshot exists, taken by hand during
  [CHG-0035](/docs/changes/2026/0035-exposed-credentials/), and the
  [recovery runbook](/docs/runbook/substrate/recovery/omada-controller-recovery/) restores from it.
  Still to do: take snapshots routinely, so a restore does not lose everything since one hand-taken
  copy
- 🔄 Keep the core router's saved configurations somewhere that survives the Builder: they are what
  [Rebuild the Core Router](/docs/runbook/substrate/recovery/rebuild-core-router/) restores from,
  and they hold the router's secrets, so the copy must be private and encrypted. `make backup-router` seals it
  into the inventory with the vault password. The first backup is committed, and a restore from
  it onto the running router was rehearsed in
  [CHG-0061](/docs/changes/2026/0061-core-router-restore-rehearsal/). Still to decide: whether
  ciphertext in the public inventory repository is private enough

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
