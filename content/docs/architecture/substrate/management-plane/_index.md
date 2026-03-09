---
title: "Management Plane"
weight: 4
bookCollapseSection: true
---

# Management Plane Architecture

### Purpose

The management plane is responsible for **provisioning, recovery, and out-of-band control** of site infrastructure.

It exists *outside* normal workload operations and may interact with multiple sites simultaneously.

> *How are sites created, repaired, and controlled without depending on themselves?*

It provides:
- provisioning services (PXE, artifacts, bootstrap tooling),
- management-plane access (builders, bastions),
- and optional out-of-band services (serial consoles, OOB access).

It does **not** host tenant workloads.

---

## Three-Tier Architecture

The management plane encompasses the **builder**, **core services**, and **extended services**:

### Builder

The out-of-band provisioning role that builds everything else. Self-contained, portable, and air-gapped capable—it provisions whichever site it's connected to:

- Artifact hosting (OS images, packages, kickstarts)
- PXE/TFTP network boot infrastructure
- Ansible controller for all substrate hosts
- Out-of-band control and recovery services

See [Builder](builder/) for the complete builder architecture.

### Core Services

The foundational tier—services that must remain operational even if all extended services are lost:

- DNS authority model and naming
- DHCP, NAT, and firewall
- Authority transitions between builder and router

See [Core Services](core-services/) for the core platform architecture.

### Extended Services

Additive services providing observability, automation runners, and access tooling. These may be rebuilt entirely from the builder and core services:

- Centralized logging and metrics
- Automation runners and CI/CD
- Jump hosts and access tooling

See [Extended Services](extended-services/) for the complete extended services architecture.

---

## Architectural Invariants

The management plane architecture is considered **correct** when:

- sites can be provisioned without depending on themselves
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
