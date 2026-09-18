---
title: "CHG-0011: Tenant Workloads Get a Resolver"
weight: 11
---

# CHG-0011: Tenant Workloads Get a Resolver

| | |
|---|---|
| **Date** | 2026-09-17 |
| **Change type** | Configuration · Deployment |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | 2026-09-17, after the fix merges |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API); tenant workloads 2040 `tdemo-app` and 2080 `eds-services` on `dv02hyp002p02` |
| **Automation** | `deevnet.mgmt` `playbooks/site.yml --limit deevnet_api`, against `ansible-inventory-deevnet/mobile`; then `terraform apply` in each tenant repo |
| **Risk** | Medium — both tenant workloads are replaced, so anything on their disks is lost. Today both are empty. |
| **Related changes** | [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/) introduced the defect |
| **Related incidents** | None |
| **Related runbooks** | [Tenant DNS](/docs/architecture/decisions/0004-tenant-dns-publication/) |

---

## Summary

Every tenant workload the Deevnet API has ever built was handed an **authoritative** DNS server
as its resolver. `dv02idn001v01` (10.20.25.21) runs PowerDNS authoritative: it answers the tenant
zones it is master for and returns REFUSED for everything else. A workload pointed at it can
resolve its own tenant's names and nothing else — not a public name, not a substrate name, not
even `api.mobile.deevnet.net`, the Deevnet API the tenant is meant to talk to.

The cause is one value doing two jobs. `Site.ResolverForwardTo` is what the core router's Unbound
forwards tenant zones to, and 10.20.25.21 is exactly right for that. The workload's cloud-init
nameserver was taken from the same field, where it is exactly wrong.

After this change the two are separate settings. A workload is given the **tenant_transit
gateway, 10.20.50.1** — the first substrate hop a tenant's SNATed traffic reaches, where the core
router answers. That router recurses *and* already forwards every tenant zone to 10.20.25.21, so
one server answers all three classes of name.

### Why CHG-0010 did not catch it

CHG-0010 verified every step of *provisioning*: the zone was created, the VM cloned, the record
published, the plan clean. All of that was correct. Nothing in it ever resolved a name **from
inside a workload**, which is the first thing any real use of a tenant does. The API's test suite
had the same blind spot — it asserted what the API writes, never what the workload can then do,
and so it passed with the broken value.

## Goal

- `dig quay.io` from inside a tenant workload returns answers, not REFUSED.
- `dig api.mobile.deevnet.net` from inside a tenant workload resolves.
- A tenant's own names still resolve from inside its workload.
- `/etc/resolv.conf` inside 2040 and 2080 names 10.20.50.1.
- A newly created workload gets 10.20.50.1 without any further action.
- The core router still forwards tenant zones to 10.20.25.21 — that behaviour is unchanged.

## Scope

**In scope:** the `WorkloadResolver` split in the API; the `deevnet_api` role and inventory
variable; redeploying the API; replacing workloads 2040 and 2080 through the provider.

**Out of scope:** the zone policy (CHG-0007 — the router is still allow-all, and this change does
not depend on that); giving tenants a way to reboot a workload in place; DNS for anything but
tenant workloads.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Replacing a workload destroys its disk | 2040, 2080 | Both are empty — nothing is deployed on either. Confirmed before running. |
| The API comes back with an empty resolver and refuses to start | dv02prv001v01 | `Site.Validate` rejects an empty `WorkloadResolver`, so a missing value fails the deploy loudly instead of building more broken workloads. `/readyz` is the check. |
| 10.20.50.1 stops answering tenants if CHG-0007 is applied later | core router | CHG-0007 must keep the tenant→router DNS path. Recorded as a follow-up on that change. |
| The old value is still right for the router forward | dv02idn001v01 | The two settings are now separate; the forward target is untouched and verified after the deploy. |

## Prerequisites

- [ ] The three fix branches merged: `deevnet-provisioning-api`, `deevnet.mgmt`,
      `ansible-inventory-deevnet` (all `fix/workload-resolver`)
- [ ] Vault decrypted, collections built
- [ ] API tagged and staged: `make image && make stage` on a clean, tagged tree
- [ ] Confirmed 2040 and 2080 hold nothing worth keeping

## Procedure

### Step 1: Deploy the API

Not disruptive to tenants — the API is provisioning-only, and nothing at runtime depends on it.

**Run:**

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --limit deevnet_api
```

**Verify:**

1. `curl --cacert site-ca.pem https://api.mobile.deevnet.net:8080/readyz` returns ready.
2. The version endpoint reports the new tag.
3. The env file on `dv02prv001v01` carries `DEEVNET_WORKLOAD_RESOLVER=10.20.50.1` and still
   carries `DEEVNET_RESOLVER_FORWARD_TO=10.20.25.21`.

**Undo:** [Undo Step 1](#undo-step-1)

### Step 2: Replace the eds workload

Disruptive to eds only. The VM is destroyed and rebuilt, which is how the new cloud-init
nameserver takes effect — Proxmox writes the config, but only a fresh boot applies it.

**Run:**

```bash
cd /srv/eds/infra/deevnet-tenant-eds
terraform apply -replace=deevnet_workload.services
```

**Verify:**

1. `services.eds.mobile.deevnet.net` still resolves to 10.20.130.10.
2. From inside VM 2080: `/etc/resolv.conf` names 10.20.50.1; `quay.io`,
   `api.mobile.deevnet.net` and `services.eds.mobile.deevnet.net` all resolve.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: Replace the tdemo workload

Same shape, for the reference tenant.

**Run:**

```bash
cd /srv/dvnt/deevnet-tenant-tdemo
terraform apply -replace=deevnet_workload.app
```

**Verify:** as Step 2, for tdemo's names and VM 2040.

**Undo:** [Undo Step 3](#undo-step-3)

## Verification

From inside each tenant workload, all three classes of name resolve through 10.20.50.1: a public
name, a substrate name, and the tenant's own. On the substrate, `dig` against 10.20.25.21 still
answers the tenant zones, confirming the forward target is unchanged. A workload created after
this change gets 10.20.50.1 with no further action.

## Undo

Backed out in reverse order. There is no point of no return: the old value is a one-line revert,
and the workloads are rebuildable from Terraform in either direction.

### Undo Step 1

Revert the inventory variable, redeploy the API. Workloads built in between keep whatever they
were given; they are repaired by replacing them.

### Undo Step 2

`terraform apply -replace=deevnet_workload.services` against the reverted API returns the old
nameserver. There is nothing on the disk to preserve in either direction.

### Undo Step 3

As Undo Step 2, for tdemo.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] A tenant has no way to restart a workload in place. Replacing it is the only lever the
      provider offers. The intended direction is that **tenant workloads are as stateless as
      possible**, so that replace stays the ordinary repair and losing a disk costs nothing —
      but that is a design goal, not a guarantee, and a configuration change that needs a boot
      should not require destroying the machine. Consider a restart action on
      `deevnet_workload`.
- [ ] CHG-0007 must keep the tenant→core-router DNS path open when the zone policy is enforced,
      or every tenant workload loses name resolution.
- [ ] The API's test suite asserts what the API writes, not what a workload can do. The
      regression test added here is the first of the latter kind; look for the same gap elsewhere.
