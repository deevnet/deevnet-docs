---
title: "Building"
weight: 4
---

# Tenant Building

How a tenant comes into existence, and what it declares to do so.

---

## The shape of it

A tenant is built by **asking the Deevnet API**, through a Terraform provider, from the tenant's own
repository ([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/)).

```
tenant repository                substrate
─────────────────                ─────────
terraform apply  ──────────────► Deevnet API
  deevnet_tenant                   allocates the index
  deevnet_workload                 creates the SDN zone, VNet, subnet
  deevnet_dns_record               builds the VM, issues its address
                                   delegates the DNS zone, issues the key
                                   issues the state-store credential
```

Everything a tenant is — its index, its network numbering, its DNS zone and key, its state
credential and its workload addressing — is **issued by the API**. There is no number to allocate
and no substrate credential to fetch. What the tenant holds is one token.

{{< hint info >}}
**This replaced an earlier flow.** A tenant used to instantiate a shared Terraform module from the
tenant factory, declare its own SDN objects, and hold a Proxmox API credential to build them with.
Its index was hand-allocated in a list that was maintained in two places and
[duly diverged](/docs/architecture/decisions/0002-tenant-fabric-numbering/). That model was retired
by [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/); the factory repository became
[`deevnet-tenant-fabric`](https://github.com/deevnet/deevnet-tenant-fabric) and now carries only
the fabric itself.
{{< /hint >}}

---

## Why Terraform for tenants

The substrate is built with automation; tenants are built with Terraform. The split is deliberate:

| Aspect | Substrate (automation) | Tenant (Terraform) |
|--------|------------------------|--------------------|
| **Change frequency** | Rare, deliberate | Frequent |
| **State model** | Procedural, idempotent | Declarative, stateful |
| **Drift detection** | Manual verification | Built into plan |
| **Lifecycle** | Configure what exists | Create and destroy |

A tenant is created and destroyed often enough that `destroy` has to work and mean something. The
substrate is configured, not created, so it does not need that and should not pay for it.

---

## What a tenant declares

The whole of a minimal tenant, from
[`deevnet-tenant-tdemo`](https://github.com/deevnet/deevnet-tenant-tdemo) — the reference a new
tenant is copied from:

```hcl
terraform {
  required_providers {
    deevnet = {
      source  = "deevnet/deevnet"
      version = "~> 0.1"
    }
  }
}

# endpoint, token and CA come from the environment. The token is the
# single-use enrollment token on the first apply, and this tenant's own
# token afterwards.
provider "deevnet" {}

resource "deevnet_tenant" "this" {
  name = var.tenant_name
}

# One workload. The API picks its VMID, MAC and address from the tenant's
# index; the tenant picks what it runs on.
resource "deevnet_workload" "app" {
  tenant    = deevnet_tenant.this.name
  name      = "app"
  cores     = var.vm_cores
  memory_mb = var.vm_memory_mb
  ssh_keys  = var.ssh_keys
}

# A name beside the workload's own, for the service rather than the machine.
resource "deevnet_dns_record" "service" {
  tenant  = deevnet_tenant.this.name
  name    = "service"
  address = deevnet_workload.app.address
}
```

**To create a tenant, copy this repository and change the name.** Nothing else in it is
tenant-specific — which is the point of moving allocation behind the API.

One naming constraint survives from the fabric: Proxmox caps SDN zone IDs at **8 characters**, and a
tenant's zone ID is its name verbatim. Tenant names must fit.

---

## Onboarding, once

Before a tenant's first apply, the substrate **admits** it. That is the one act that is a substrate
commit; everything after it is the tenant's own.

1. **The substrate issues a single-use enrollment token.** It is delivered encrypted to the tenant's
   consumer ([ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/)).
2. **The tenant applies.** The API allocates its index, builds its network and workloads, delegates
   its DNS zone, and returns a token of the tenant's own. The enrollment token is spent.
3. **The tenant migrates its state**, if it is taking the offered store. The credentials are outputs
   of the first apply, so the backend is configured after it, with
   `terraform init -migrate-state` — or the tenant keeps custody of its own state and skips this
   entirely ([ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/)).

---

## What lands on the substrate

For a tenant at index `n` on `mobile`, everything derives from that one number
([ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/)):

| Object | Derivation | `eds` (index 2) |
|--------|-----------|-----------------|
| EVPN zone, which **is** the VRF | the tenant's name | `eds`, `vrf-vxlan 10002` |
| VNet | `20000 + n×10` | `eds0`, tag `20020` |
| Subnet, with SNAT | `10.20.{128+n}.0/24` | `10.20.130.0/24` |
| Anycast gateway | `.1` of that subnet | `10.20.130.1` |
| Workload addresses | `.10` upward, by ordinal | `10.20.130.10` |
| DNS zone | `<tenant>.<site>.deevnet.net` | `eds.mobile.deevnet.net` |

Workloads are addressed by **cloud-init, not DHCP** — Proxmox implements SDN DHCP in Simple zones
only, and a tenant's zone is an EVPN zone. The address is derived from the index rather than
leased, which matches the deterministic addressing the rest of the estate uses.

---

## What the tenant supplies beyond this

The API builds the tenant's infrastructure. It does **not** deliver the tenant's application —
that is the tenant's own, pulled by the workload rather than pushed by the substrate
([ADR-0017](/docs/architecture/decisions/0017-tenant-code-delivery/)). The boundary is between
*operating* a machine and *owning what runs on it*, and it is a rule rather than a physical fact
now that operators can reach tenant workloads
([ADR-0018](/docs/architecture/decisions/0018-operator-access-to-tenants/)).

A tenant that owns physical devices declares those too, through the same provider — but a device
never joins the tenant's network. See [Edge Devices](/docs/architecture/edge-devices/).

---

## Rebuild

A tenant is rebuilt by applying its repository against a substrate. Because the tenant declares
what it is rather than where it sits, and the API issues the rest, the same code rebuilds it on a
rebuilt hypervisor — or, in principle, at another site — without editing. The index is reallocated
from the registry, and a tenant's index is never reused while that tenant exists.
