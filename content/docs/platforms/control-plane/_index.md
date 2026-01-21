---
title: "Control Plane"
weight: 2
bookCollapseSection: true
---

# Control Plane

The **control plane** provides infrastructure services required to provision, manage, and operate the substrate. These are the foundational systems that must be operational before tenant workloads can run.

---

## Control Plane Components

| Component | Purpose |
|-----------|---------|
| **Bootstrap Node** | Ansible controller, artifact server, PXE boot infrastructure |
| **Management Hypervisor** | Hosts observability, automation, and access services |

---

## Characteristics

Control plane infrastructure is:

- **Infrastructure-critical** — Must remain available to support recovery and rebuild operations
- **Slow change cadence** — Changes are deliberate and carefully tested
- **Manually provisioned** — Initial setup requires physical access or manual intervention
- **Ansible-managed** — Day-2 configuration via Ansible, not Terraform

---

## Recovery Model

The control plane is designed for recoverability:

1. **Bootstrap node** can rebuild the entire substrate from staged artifacts
2. **Management hypervisor** hosts are rebuilt from Packer templates
3. **Configuration is code** — All settings are in Git, not in the running systems

If the management hypervisor fails, the bootstrap node can reprovision it. If the bootstrap node fails, it can be rebuilt from a fresh OS install and the Git repositories.

---

## Separation from Tenant Compute

Control plane infrastructure is deliberately separated from tenant workloads:

| Aspect | Control Plane | Tenant Compute |
|--------|---------------|----------------|
| **Change cadence** | Slow, deliberate | Fast, experimental |
| **Blast radius** | Must be minimized | Tolerable |
| **Rebuild tolerance** | Low — avoid rebuilds | High — expect rebuilds |
| **Provisioning** | Ansible | Terraform (future) |

This separation ensures that tenant experimentation cannot impact substrate stability.
