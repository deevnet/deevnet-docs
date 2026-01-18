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
- **Reproducibility** — Recreate tenant environments reliably
- **Drift detection** — Identify manual changes
- **Lifecycle automation** — Create, update, destroy via automation

---

## Terraform-First Approach

Unlike substrate infrastructure (Ansible-first), tenant workloads use **Terraform**:

| Aspect | Substrate (Ansible) | Tenant (Terraform) |
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

  network = {
    vlan_id = 100  # grooveiq VLAN
    ip      = "10.100.0.10"
    gateway = "10.100.0.1"
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
- DNS records are created (may be automated via Terraform)
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
| **Tool** | Ansible | Terraform |
| **Hypervisor** | Management plane | Tenant hypervisor |
| **Lifecycle** | Long-lived, stable | Frequent create/destroy |
| **Authority** | Platform admins | May delegate to tenant admins |

The substrate [Builder](/docs/architecture/substrate/builder/) provisions
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

Before provisioning tenant VMs:

1. **VLAN configured** — Core Router has tenant VLAN interface
2. **DHCP scope exists** — Either dynamic pool or static reservations
3. **Firewall zone defined** — Tenant security policies in place
4. **DNS zone ready** — Zone exists for `tenant.substrate.deevnet.net`

These are substrate-level prerequisites managed by the substrate builder.

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
