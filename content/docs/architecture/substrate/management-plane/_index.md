---
title: "Management Plane"
weight: 2
bookCollapseSection: true
---

# Management Plane Architecture

### Purpose

The management plane is responsible for **provisioning, recovery, and out-of-band control** of substrates.

It exists *outside* normal workload substrates and may interact with multiple substrates simultaneously.

> *How are substrates created, repaired, and controlled without depending on themselves?*

It provides:
- provisioning services (PXE, artifacts, bootstrap tooling),
- management-plane access (builders, bastions),
- and optional out-of-band services (serial consoles, OOB access).

It does **not** host tenant workloads.

---

## Three-Tier Architecture

The management plane encompasses the **builder**, **core services**, and **virtual services**:

### Builder (Bootstrap Node)

The out-of-band provisioning machine that builds everything else. Self-contained, portable, and air-gapped capable—it provisions whichever substrate it's connected to:

- Artifact hosting (OS images, packages, kickstarts)
- PXE/TFTP network boot infrastructure
- Ansible controller for all substrate hosts
- Out-of-band control and recovery services

See [Builder](builder/) for the complete builder architecture.

### Core Services (Physical)

The foundational tier—dedicated hardware services that must remain operational even if all virtual infrastructure is lost:

- DNS authority model and naming
- DHCP, NAT, and firewall
- Authority transitions between builder and router

See [Core Services](core-services/) for the core platform architecture.

### Virtual Services (Hypervisor)

Additive services running on a dedicated management hypervisor—observability, automation runners, and access tooling. These may be rebuilt entirely from the builder and core services:

- Centralized logging and metrics
- Automation runners and CI/CD
- Jump hosts and access tooling

See [Virtual Services](virtual-services/) for the complete virtual layer architecture.

---

## Architectural Invariants

The management plane architecture is considered **correct** when:

- substrates can be provisioned without depending on themselves
- management services have stable DNS identities
- provisioner hosts are replaceable without consumer impact
- multi-homed reachability is explicit in naming
- substrates remain authoritative only for substrate concerns

If a substrate must be "mostly working" in order to be rebuilt, the architecture is incorrect.

---

## Relationship to Other Documents

This document defines **what exists**.

Related documents define:
- **Correctness** — invariants that must always hold
- **Secure Identity** — how access and secrets are handled
- **Provisioning Architecture** — how management services are used during bootstrap
- **Standards** — naming, DNS, and access rules derived from this model
