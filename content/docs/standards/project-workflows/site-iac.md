---
title: "Site IaC"
weight: 2
---

# Site IaC Workflow

Template for full infrastructure site builds involving bare-metal provisioning, network automation, and end-to-end rebuild validation. Use this for complex, multi-layer infrastructure projects.

For simpler automation projects, see [IaC/CaC](../iac-cac/).

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

Define the infrastructure domain and automation goals.

**In Scope**
- Target infrastructure components
- Automation tooling
- Provisioning and configuration scope
- Operational boundaries

**Out of Scope**
- Systems managed by other teams/projects
- Application-layer concerns
- Features deferred to future phases

---

## Milestone: Provisioning Automation ⏳

Core infrastructure for building and deploying the site.

| Task | Status |
|------|--------|
| Automation tooling setup (collections, modules) | ⏳ |
| Base image creation and packaging | ⏳ |
| Bootstrap node provisioning | ⏳ |
| Hypervisor/platform provisioning | ⏳ |
| Automated install mechanisms | ⏳ |
| Artifact hosting and distribution | ⏳ |
| Air-gap/offline support (if required) | ⏳ |

---

## Milestone: Inventory & Standards ⏳

Documentation and inventory definitions.

| Task | Status |
|------|--------|
| Documentation site or repository | ⏳ |
| Standards and correctness definitions | ⏳ |
| Inventory structure and conventions | ⏳ |
| Host and group variable organization | ⏳ |
| Secrets management approach | ⏳ |

---

## Milestone: Network & Service Automation ⏳

Automated configuration of network infrastructure and services.

| Task | Status |
|------|--------|
| DHCP/IPAM automation | ⏳ |
| DNS automation | ⏳ |
| Firewall/router configuration | ⏳ |
| VLAN and segmentation design | ⏳ |
| Switch configuration automation | ⏳ |
| Wireless AP automation | ⏳ |
| Load balancer/reverse proxy configuration | ⏳ |
| Certificate management | ⏳ |

---

## Milestone: Full Rebuild Validation ⏳

End-to-end rebuild of the infrastructure from scratch.

| Step | Task | Status |
|------|------|--------|
| 1 | Rebuild bootstrap/provisioner node | ⏳ |
| 2 | Fetch artifacts (ISOs, images, packages) | ⏳ |
| 3 | Enable bootstrap-authoritative mode | ⏳ |
| 4 | Configure network infrastructure | ⏳ |
| 5 | Rebuild core services | ⏳ |
| 6 | Rebuild compute/hypervisor layer | ⏳ |
| 7 | Rebuild application workloads | ⏳ |
| 8 | Validate end-to-end functionality | ⏳ |

Validates disaster recovery and reproducibility.

---

## Milestone: Day 2 Operations ⏳

Ongoing maintenance and operational procedures.

| Task | Status |
|------|--------|
| Patching strategy - infrastructure components | ⏳ |
| Patching strategy - operating systems | ⏳ |
| Patching strategy - applications | ⏳ |
| Backup and restore procedures | ⏳ |
| Monitoring and alerting | ⏳ |
| Log aggregation and retention | ⏳ |
| Capacity planning | ⏳ |
| Runbook documentation | ⏳ |
