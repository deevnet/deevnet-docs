---
title: "Builder"
weight: 4
---

# Substrate Builder Architecture

The **builder** is the architectural role responsible for provisioning and configuring
all substrate infrastructure. This role is implemented by the bootstrap node.

---

## Purpose

Every substrate needs a way to be created from scratch:

> *How do you provision infrastructure when no infrastructure exists yet?*

The builder answers this question by providing:
- A self-contained provisioning platform
- All artifacts needed for air-gapped deployment
- Automation to configure every substrate component
- Authority transition from bootstrap to production

---

## Architectural Role

The builder exists at the **management plane** layer of substrate infrastructure:

```
┌─────────────────────────────────────────────────────────┐
│              Substrate Infrastructure                   │
├─────────────────────────────────────────────────────────┤
│  Management Plane    │ Builder (provisioning,             │
│                   │ artifacts, PXE/TFTP)               │
├───────────────────┼─────────────────────────────────────┤
│  Network          │ Core Router (gateway, firewall,    │
│                   │ DNS, DHCP)                         │
├───────────────────┼─────────────────────────────────────┤
│  Compute          │ Proxmox hypervisors, embedded      │
│                   │ devices                            │
└───────────────────┴─────────────────────────────────────┘
```

The builder provisions and configures everything else in the stack.

---

## Key Properties

### Self-Contained

The builder must contain everything needed to stand up a substrate:
- Automation code (Ansible collections, playbooks)
- Artifact server (OS images, packages, kickstarts)
- Network boot infrastructure (TFTP, GRUB configs)
- Git repositories for all IaC

### Portable

A single builder can move between substrates:
- Same physical device serves dvntm or dvnt
- Provisions whichever environment it's connected to
- No substrate-specific hardware requirements

### Air-Gapped Capable

Once artifacts are staged, the builder can provision without upstream internet:
- All required images stored locally
- No external dependencies during provisioning
- Critical for isolated or bandwidth-limited deployments

### Disposable Authority

The builder has temporary authority during bootstrap:
- May serve as DNS/DHCP/gateway initially
- Hands off control to Core Router once configured
- Becomes a regular admin host in production

---

## Authority Transition

The builder participates in explicit authority transitions:

| Phase | Builder Role | Core Router Role |
|-------|-------------|------------------|
| **Bootstrap** | DNS, DHCP, gateway, TFTP, artifacts | Does not exist |
| **Transition** | TFTP, artifacts | DNS, DHCP, gateway |
| **Production** | TFTP, artifacts, Ansible controller | DNS, DHCP, gateway, firewall |

The transition is explicit and deliberate—never automatic.

---

## Relationship to Tenants

The builder provisions **substrate infrastructure only**:
- Core Router configuration
- Hypervisor setup
- Management plane VMs
- Network switch and AP configuration

Tenant workloads use a different provisioning model. See
[Tenant Building](/docs/architecture/tenant/building/) for tenant-specific
provisioning architecture.

---

## Implementation

The builder role is implemented by the **bootstrap node**:

| Aspect | Implementation |
|--------|----------------|
| **Hardware** | Mini PC with dual NICs |
| **OS** | Fedora with `deevnet.builder` collection |
| **Artifacts** | nginx serving images and packages |
| **Network boot** | in.tftpd with GRUB configs |
| **Automation** | Ansible controller for all substrate hosts |

See [Bootstrap Node](/docs/platforms/management-plane/bootstrap-node/) for implementation details.

---

## Design Principles

### Ansible-First

All substrate provisioning uses Ansible:
- Idempotent configuration
- Version-controlled playbooks
- Traceable changes
- No Terraform for substrate infrastructure

### Deterministic Identity

All provisioned hosts receive:
- Deterministic MAC addresses (for VMs)
- Static DHCP reservations
- Predictable DNS records
- Inventory-defined identity

### Explicit Authority

Authority transitions are:
- Documented in runbooks
- Triggered manually
- Validated before completion
- Never automatic

---

## Summary

1. The builder is the management plane for substrate provisioning
2. Self-contained, portable, and air-gapped capable
3. Has temporary authority during bootstrap, transitions to admin role
4. Provisions substrate infrastructure only (not tenants)
5. Implemented by the bootstrap node using Ansible
