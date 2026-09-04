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
| A DNS zone of your own | `<tenant>.<site>.deevnet.net`, plus its reverse — you author the records |

What you supply is the Terraform that declares it. Everything is code — a tenant is rebuilt from
its own repository, not from a backup. That includes your names: the substrate gives you the zone
and the key to write it with, and never writes a record on your behalf.

---

## Prerequisites

**Two clones**, because onboarding and the tenant lifecycle live in different places
([ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/)):

- [`deevnet-tenant-factory`](https://github.com/deevnet/deevnet-tenant-factory) — to allocate the
  index, copy the reference implementation, and issue the fabric attachment. Substrate side.
- `deevnet-tenant-<name>` — the tenant's own repository, which is where every apply happens.

Also:

- `terraform` on your PATH, and an ssh-agent that can reach GitHub (the tenant module is fetched by
  git tag at `init`)
- Read access to the Deevnet inventory vault (credentials are rendered from it, never stored)
- Your tenant's TSIG secret, exported as `TF_VAR_tsig_key_secret` — the substrate issues it during
  onboarding (step 2) and it is what lets the tenant publish its own names
- If you want the state store, your state credential as `AWS_ACCESS_KEY_ID` /
  `AWS_SECRET_ACCESS_KEY`. It is optional
  ([ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/))

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

## 2. Onboard the tenant on the substrate

Two substrate steps go with a new index, both driven from the same declared list and both done
**once**. After this, nothing you do to the tenant touches a substrate repository again.

Add the tenant to `deevnet_tenants` in `ansible-inventory-deevnet/<site>/group_vars/all/tenants.yml`:

```yaml
deevnet_tenants:
  - name: tdemo
    index: 1
  - name: grooveiq
    index: 2
```

Generate a TSIG secret and put it in the vault under `vault_tenant_tsig_keys['grooveiq']`:

```bash
openssl rand -base64 32
```

Then run the two substrate plays:

```bash
# Egress: give the tenant VRF a way out (ADR-0003)
cd ansible-collection-deevnet.net
ansible-playbook playbooks/proxmox-node-network.yml --tags tenant-egress

# DNS: create the tenant's zones, issue and bind its key (ADR-0004)
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --limit tenant_dns --tags tenant-dns

# Delegation: point the resolver at them
cd ../ansible-collection-deevnet.net
ansible-playbook playbooks/opnsense.yml --tags tenant-dns
```

Egress must be applied **after** the tenant's Terraform has created the VRF, so in practice this
step is split: register the tenant and do the DNS half now, and run the egress tags after step 4.

## 3. Create the tenant's repository

A tenant is its own repository. Create `deevnet-tenant-grooveiq` and fill it from the reference
implementation — a copy **out** of the factory, not into it:

```bash
cp -r examples/tenant/. ../deevnet-tenant-grooveiq/
```

The example cannot be applied as it stands: it ships with `tenant_index = 0`, which the module
rejects. That is deliberate, so an unedited copy fails loudly rather than quietly becoming a second
tenant with someone else's name. Replace every `REPLACE-ME`, and set the two values that actually
differ, in `terraform.tfvars`:

```hcl
tenant_name  = "grooveiq"   # <= 8 chars
tenant_index = 2            # from TENANTS.md
```

Then have the substrate issue the fabric attachment — run this **in the factory**:

```bash
make tenant-attachment TENANT=../deevnet-tenant-grooveiq
```

That writes `fabric.auto.tfvars` with the controller and node. A tenant never *invents* them: the
substrate hands them over at onboarding, in the same act that issues the TSIG key and the egress.
They used to be read out of the fabric's Terraform state, which only worked while tenants lived
inside the factory.

If you want the state store, uncomment the `backend "s3"` block and set its key to
`tenants/grooveiq/terraform.tfstate`. Leaving it commented is a valid choice — you then carry your
own custody.

## 4. Apply

Everything from here happens **in the tenant's repository**:

```bash
cd ../deevnet-tenant-grooveiq
make init      # fetches the tagged module - needs GitHub and your ssh-agent
make plan
make apply
```

Credentials are rendered from the inventory vault by the targets themselves; nothing is stored in
the repo. `AUTO=1` skips the approval prompt for non-interactive runs.

This creates the tenant's EVPN zone (its VRF), its VNet, its subnet, and its VMs.

**The module is pinned by tag**, and `init` vendors it into `.terraform/modules/`. Neither `plan`
nor `apply` re-fetches it, so moving to a newer module version takes an explicit
`terraform init -upgrade` — a repository that never re-inits stays on its old module indefinitely,
quietly.

## 5. Verify

```bash
terraform output
```

Then confirm the things that actually matter:

| Check | Expected |
|-------|----------|
| VM address | `10.20.130.10` upward — `.1` is the gateway, `.2-.9` are reserved for the fabric |
| Gateway | `ping 10.20.130.1` from the VM answers |
| Egress | `curl ifconfig.me` succeeds |
| Perimeter | The core router sees source `10.20.50.22`, never `10.20.130.0/24` |
| Isolation | Another tenant's subnet is unreachable |
| Forward DNS | `dig @10.20.99.1 grooveiq-1.grooveiq.dvntm.deevnet.net +short` answers `10.20.130.10` |
| Reverse DNS | `dig @10.20.99.1 -x 10.20.130.10 +short` answers the same name |
| Namespace | An update signed with another tenant's key is **REFUSED** for your zone |

## 6. Destroy

```bash
make destroy    # in the tenant's own repository
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

**Your names are not in the resolver you query.** Workloads resolve through the core router, but the
core router holds none of your records. It delegates your zone to the tenant DNS server, which is
authoritative for it. That is why an `opnsense_dns` run cannot delete your records — they were never
there ([ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/)).

**You cannot publish outside your own zone, and this is enforced.** Your TSIG key is bound to your
zones by server-side metadata. An update aimed at another tenant's zone comes back REFUSED from
PowerDNS; it is not a convention your Terraform is trusted to respect.

**Destroying the tenant removes its names.** The records are in your Terraform state, so
`make tenant-destroy` takes them with it. The zone and the key survive — those are substrate
onboarding, not tenant content — so re-applying restores every name with no substrate action.
