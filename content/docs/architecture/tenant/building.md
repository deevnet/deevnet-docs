---
title: "Building"
weight: 3
---

# Tenant Building

Defines the provisioning model for tenant workloads.

---

## Purpose

Tenant building provides:
- **Declarative infrastructure** — Define tenant environments as code
- **Rebuild from scratch** — A tenant is fully reconstituted from its own code against the substrate: overlay network, VMs, and DNS
- **Reproducibility** — Recreate tenant environments reliably
- **Drift detection** — Identify manual changes
- **Lifecycle automation** — Create, update, destroy via automation

---

## Terraform-First Approach

Unlike substrate infrastructure (automation-first), tenant workloads use **Terraform**:

| Aspect | Substrate (Automation) | Tenant (Terraform) |
|--------|--------------------|--------------------|
| **Change frequency** | Rare, deliberate | Frequent, agile |
| **State model** | Procedural, idempotent | Declarative, stateful |
| **Drift detection** | Manual verification | Built-in plan/apply |
| **Lifecycle** | Configure existing | Create/destroy |
| **Use case** | Infrastructure config | VM provisioning |

### Why Terraform for Tenants?

1. **Declarative definitions** — Define what should exist, not how to create it
2. **State tracking** — Know exactly what's deployed
3. **Plan before apply** — Preview changes before execution
4. **Destroy support** — Clean up tenant resources completely
5. **Proxmox provider** — Native Terraform support for VM lifecycle

---

## Tenant Provisioning Workflow

### 1. Define Tenant Infrastructure

Create Terraform configuration for tenant VMs:

```hcl
# Example: grooveiq tenant
module "grooveiq_api" {
  source = "../modules/proxmox-vm"

  name        = "api-vm01"
  target_node = "pve-tenant"
  template    = "fedora-43-template"

  cores   = 2
  memory  = 4096
  disk    = "32G"

  # Attach to the tenant's own overlay network in the fabric — not a core-router VLAN
  network = {
    fabric_net = "grooveiq"     # the tenant's overlay, defined in the tenant's own code
    ip         = "10.100.0.10"  # from the tenant's own subnet / fabric IPAM
    gateway    = "10.100.0.1"   # anycast gateway hosted by the fabric
  }
}
```

### 2. Plan Changes

```bash
terraform plan
```

Review what will be created, modified, or destroyed.

### 3. Apply Changes

```bash
terraform apply
```

Terraform creates or updates VMs on the tenant hypervisor.

### 4. Post-Provisioning

After VMs are created:
- Ansible applies application-level configuration
- DNS records are created as part of the Terraform configuration
- Monitoring is configured

---

## Template Requirements

Tenant VMs clone from Proxmox templates:

| Requirement | Description |
|-------------|-------------|
| **Cloud-init** | Template must support cloud-init for initial config |
| **SSH key injection** | Automation user SSH key injected at boot |
| **Network config** | DHCP or static IP via cloud-init |
| **Base packages** | Python3 for Ansible, basic utilities |

Templates are built by the [Image Factory](/docs/platforms/) and stored
on the tenant hypervisor.

---

## Tenant Inventory Structure

Tenant infrastructure is tracked in a separate inventory:

```
tenant-inventory/
├── grooveiq/
│   ├── hosts.yml
│   ├── group_vars/
│   └── terraform/
├── vintronics/
│   ├── hosts.yml
│   ├── group_vars/
│   └── terraform/
└── moneyrouter/
    ├── hosts.yml
    ├── group_vars/
    └── terraform/
```

This separation:
- Keeps tenant state isolated
- Allows tenant-specific variables
- Enables independent lifecycle management

---

## Distinction from Substrate Builder

| Aspect | Substrate Builder | Tenant Building |
|--------|-------------------|-----------------|
| **Target** | Substrate infrastructure | Tenant workloads |
| **Tool** | Automation | Terraform |
| **Hypervisor** | Management plane | Tenant hypervisor |
| **Lifecycle** | Long-lived, stable | Frequent create/destroy |
| **Authority** | Platform admins | May delegate to tenant admins |

The substrate [Builder](/docs/architecture/builder/) provisions
the infrastructure that tenant building runs on top of.

---

## MAC Address Policy

For tenant VMs, MAC addresses may be:

| Policy | When Used |
|--------|-----------|
| **Auto-generated** | Default for ephemeral/test VMs |
| **Deterministic** | When stable identity is required |

If deterministic MACs are needed:
- Define MAC in Terraform configuration
- Store in tenant inventory
- Create corresponding DHCP reservation

This is optional for tenants, unlike management-plane VMs where
deterministic MACs are mandatory.

---

## Network Prerequisites

Under the tenant fabric model, a tenant **owns its own network** and creates it as part of its own
code — a virtual overlay in the fabric with its subnet, anycast gateway, and DHCP. Configuring a
per-tenant VLAN on the core router is **not** a build step.

What the substrate must provide first (the substrate side of the [tenant contract](/docs/architecture/tenant/#the-tenant-contract)):

1. **Tenant fabric present** — the tenant hypervisor runs the overlay fabric the tenant attaches to
2. **Perimeter transit** — the core router provides the transit boundary for tenant egress and shared-service access
3. **DNS zone** — the substrate zone the tenant publishes its records into

The tenant's overlay network, addressing, and DNS records are all created by the tenant's own
Terraform — not as substrate prerequisites. See
[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/).

---

## State Management

### Terraform State

Tenant Terraform state should be:
- Stored in version control (for small deployments)
- Or in remote backend (for team access)
- Never edited manually

### Drift Handling

If manual changes are detected:
1. Run `terraform plan` to identify drift
2. Either:
   - Update Terraform config to match reality
   - Or run `terraform apply` to enforce desired state

---

## Summary

1. Tenant workloads use Terraform (not Ansible) for provisioning
2. Declarative definitions enable reproducibility and drift detection
3. VMs clone from cloud-init enabled templates
4. Tenant inventory is separate from substrate inventory
5. MAC addresses may be auto-generated or deterministic (optional)
6. Substrate builder provides the infrastructure that tenants run on
