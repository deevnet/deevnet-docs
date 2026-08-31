---
title: "Provisioning a Tenant"
weight: 8
---

# Provisioning a Tenant

How to create, verify and destroy a tenant on the dvntm substrate.

This is the operational procedure. The *why* is
[ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/) (the fabric model) and
[ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/) (the numbering); the
conceptual model is [Tenant Building](/docs/architecture/tenant/building/).

---

## What the substrate gives you

A tenant is **not** a VLAN, and creating one requires no switch change, no core router change, and
no ticket. The tenant hypervisor runs an EVPN fabric; a tenant is an isolated routing domain
inside it.

| You get | Detail |
|---------|--------|
| An isolated routing domain | One VRF per tenant — traffic cannot reach another tenant's |
| A `/24` of your own | Allocated from `10.20.128.0/18` |
| An anycast gateway | `.1` of your subnet, hosted by the fabric |
| Outbound internet | SNAT at the fabric exit node, via the perimeter |
| VMs from a base image | Fedora, cloud-init enabled |

What you supply is the Terraform that declares it. Everything is code — a tenant is rebuilt from
its own repository, not from a backup.

---

## Prerequisites

- Clone of [`deevnet-tenant-factory`](https://github.com/deevnet/deevnet-tenant-factory)
- `terraform` on your PATH
- Read access to the Deevnet inventory vault (credentials are rendered from it, never stored)

---

## 1. Allocate a tenant index

**Do this first.** Every identifier a tenant uses — its VRF, its VNets, its subnet — is derived
from a single number, so this is the one decision that can collide with another tenant.

Open `TENANTS.md`, take the next free index, and add your row:

| Index | Tenant | VRF VNI | VNet VNI(s) | Overlay subnet | Status |
|------:|--------|--------:|-------------|----------------|--------|
| 2 | `grooveiq` | 10002 | 20020 | 10.20.130.0/24 | active |

For index `n` on dvntm, everything follows:

| Identifier | Formula | `n = 2` |
|---|---|---|
| VRF VXLAN | `10000 + n` | 10002 |
| VNet VNI | `20000 + n*10 + i` | 20020 |
| Subnet | `10.20.{128+n}.0/24` | 10.20.130.0/24 |
| Gateway | `.1` of that subnet | 10.20.130.1 |

Never reuse an index while its tenant exists, and never hand-pick a VNI — an identifier that
happens to be free on this node today will collide the moment the fabric gains a second member.

> **Names are capped at 8 characters**, lowercase alphanumeric, starting with a letter. Proxmox
> limits SDN zone and VNet IDs to 8 characters and the zone ID *is* the tenant name. The module
> validates this so you find out at `plan` rather than from the API.

## 2. Create the tenant directory

Copy the demo tenant and change two values:

```bash
cp -r tenants/dvntm/t-demo tenants/dvntm/grooveiq
```

In `tenants/dvntm/grooveiq/main.tf`:

```hcl
module "tenant" {
  source = "../../../modules/tenant"

  tenant_name  = "grooveiq"   # <= 8 chars
  tenant_index = 2            # from TENANTS.md

  controller_id = data.terraform_remote_state.fabric.outputs.controller_id
  node          = data.terraform_remote_state.fabric.outputs.node

  template_vm_id = var.template_vm_id
  vm_count       = 2
  ssh_keys       = var.ssh_keys
}
```

The controller and node are read from the fabric's own state rather than hardcoded, so a tenant
does not need to know which hypervisor it lands on.

## 3. Apply

```bash
make tenant-init  TENANT=tenants/dvntm/grooveiq
make tenant-plan  TENANT=tenants/dvntm/grooveiq
make tenant-apply TENANT=tenants/dvntm/grooveiq
```

Credentials are rendered from the inventory vault by the targets themselves; nothing is stored in
the repo. `AUTO=1` skips the approval prompt for non-interactive runs.

This creates the tenant's EVPN zone (its VRF), its VNet, its subnet, and its VMs.

## 4. Verify

```bash
terraform -chdir=tenants/dvntm/grooveiq output
```

Then confirm the things that actually matter:

| Check | Expected |
|-------|----------|
| VM address | `10.20.130.10` upward — `.1` is the gateway, `.2-.9` are reserved for the fabric |
| Gateway | `ping 10.20.130.1` from the VM answers |
| Egress | `curl ifconfig.me` succeeds |
| Perimeter | The core router sees source `10.20.50.22`, never `10.20.130.0/24` |
| Isolation | Another tenant's subnet is unreachable |

## 5. Destroy

```bash
make tenant-destroy TENANT=tenants/dvntm/grooveiq
```

Removes the VMs and the tenant's SDN objects. Release the index in `TENANTS.md` in the same change.

Re-applying rebuilds the tenant identically — that is the property the whole model rests on, and
it is worth exercising deliberately rather than assuming.

---

## Things that surprise people

**Addresses are assigned, not leased.** Proxmox implements SDN DHCP for *Simple* zones only; EVPN
zones have no DHCP at all. Workloads are addressed by cloud-init from the tenant's subnet, so
addressing is deterministic and declared rather than dynamic. The fabric still owns the address
space, the gateway and the isolation.

**The template VMID changes.** Proxmox assigns the next free ID on every image rebuild rather than
reusing one, so `template_vm_id` needs updating after the image factory runs.

**Your tenant never appears on the core router.** No VLAN interface, no DHCP scope, no per-tenant
firewall rule. The perimeter sees only the aggregate transit network, because traffic is SNATed at
the fabric exit node on the way out. If you are looking for your subnet on the router, you will not
find it — that is the design working.

**Isolation is the VRF, not a firewall rule.** Tenants cannot reach each other because they are in
separate routing domains, not because something is filtering between them.
