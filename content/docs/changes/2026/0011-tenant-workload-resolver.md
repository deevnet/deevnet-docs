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
| **Status** | **Complete.** All three steps are done and verified. Step 3 was run as a full destroy-and-rebuild at the operator's request, which proved the fix on the create path as well as the repair path. |
| **Window** | Started 2026-09-17; Steps 1–2 ran 2026-09-17/18 |
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
- The core router still forwards tenant zones to 10.20.25.21 — that behavior is unchanged.

## Scope

**In scope:** the `WorkloadResolver` split in the API; the `deevnet_api` role and inventory
variable; redeploying the API; replacing workloads 2040 and 2080 through the provider.

**Out of scope:** the zone policy (CHG-0007 — the router was still allow-all when this ran; it was applied on 2026-09-19, and this change does
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

| When | Steps | What happened |
|---|---|---|
| 2026-09-17 | Prereqs | api#8, mgmt#27, inv#39 merged. API tagged `v0.2.6`, `make image`, `make stage`. A missing prerequisite surfaced here — see departures. |
| 2026-09-18 | Step 1 | `site.yml --limit deevnet_api`: `ok=109 changed=12 failed=0`. `/version` reports v0.2.6 (commit f26617a), `/readyz` 200, and the env file carries `DEEVNET_WORKLOAD_RESOLVER=10.20.50.1` alongside an unchanged `DEEVNET_RESOLVER_FORWARD_TO=10.20.25.21`. |
| 2026-09-18 | Step 2 | `terraform apply -replace=deevnet_workload.services`: 1 added, 1 destroyed, 34s. Identity came back unchanged — VMID 2080, MAC `02:de:20:00:08:20`, 10.20.130.10 — as the derived-identity rule requires. |
| 2026-09-18 | Step 3 | **Run as a clobber-and-rebuild instead of a replace**, at the operator's request — see departures. tdemo was deleted through the API and rebuilt from admission. Every derived value returned identical: index 1, ordinal 0, VMID 2040, MAC `02:de:20:00:07:f8`, 10.20.129.10. |

**What Step 2 proved**, from inside the rebuilt VM, using the system resolver rather than the
config file:

```
quay.io                          -> 184.193.3.126     (was REFUSED)
api.mobile.deevnet.net           -> 10.20.25.20       (was REFUSED)
services.eds.mobile.deevnet.net  -> 10.20.130.10      (worked before, still works)
registry.fedoraproject.org       rcode=0, 2 answers
```

This is the first time a tenant workload on this substrate has resolved a public name.

**What Step 3 proved, and it is more:** tdemo was destroyed entirely — workload, tenant, zone,
TSIG key, state credential — and rebuilt from a fresh `POST /v1/admissions` with no prior
credential. The new VM resolved public names **on first boot, with no intervention**:

```
quay.io                          -> 44.217.119.106
registry.fedoraproject.org       rcode=0, 2 answers
api.mobile.deevnet.net           -> 10.20.25.20
services.eds.mobile.deevnet.net  -> 10.20.130.10     (another tenant's name, still resolves)
```

So the fix holds on the **create** path, not only on the repair path — which is what matters,
because every future tenant arrives that way. The rebuild also incidentally confirmed that a
destroyed tenant returns with identical derived identity, and that `terraform plan` is clean
against the re-migrated MinIO backend.

### Departures from the plan

- **A prerequisite was missing.** The plan said "tag and stage" and stopped there, but the
  `deevnet_api` role **pins** `deevnet_api_version`; staging a tarball does not deploy it. Caught
  before Step 1 ran and added to Prerequisites. The role does carry a "Confirm the running API is
  the pinned version" task, so the play would have failed rather than silently redeploying the old
  image — the gap was in the plan, not the automation.
- **Step 3 became a destroy-and-rebuild, not a replace.** The operator asked for tdemo to be
  clobbered rather than repaired, to see the fix land in a genuinely new build. It needed none of
  tdemo's old credentials — only the operator token — and it exercised admission, tenant creation,
  networking, the workload and DNS publication end to end. A strictly better test than the planned
  step, and the plan's Step 3 is left as written above.
- **Verification went further than written.** The plan asked that `/etc/resolv.conf` name
  10.20.50.1. On a systemd-resolved host `/etc/resolv.conf` names the local stub `127.0.0.53`, so
  the check was taken from `resolvectl status` and, more usefully, from what
  `socket.gethostbyname` actually returns. Checking the config file alone would have looked like a
  failure while the system worked.

## Follow-ups

- [ ] A tenant has no way to restart a workload in place. Replacing it is the only lever the
      provider offers. The intended direction is that **tenant workloads are as stateless as
      possible**, so that replace stays the ordinary repair and losing a disk costs nothing —
      but that is a design goal, not a guarantee, and a configuration change that needs a boot
      should not require destroying the machine. Consider a restart action on
      `deevnet_workload`.
- [ ] CHG-0007 must keep the tenant→core-router DNS path open when the zone policy is enforced,
      or every tenant workload loses name resolution.
- [ ] **Deleting a tenant does not purge its Terraform state, so the next tenant of that name
      inherits it.** `minio.Remove` (`internal/backend/minio/minio.go:97`) removes the MinIO
      *user* and *policy* and nothing under the prefix. Observed during Step 3: after tdemo was
      deleted and re-admitted, the **new** tenant's credential could list the **old** tenant's
      `tenants/tdemo/terraform.tfstate`, written before the deletion. That state holds the prior
      tenant's TSIG key, state secret and API token. They are revoked at delete, so these are dead
      credentials rather than live ones — but an operator deleting a tenant would reasonably
      expect its state gone, and if a name were ever reused by a different party they would
      inherit the previous party's state and infrastructure layout. This is the same class as the
      reverse-zone PTR defect already fixed in CHG-0010, which is purged when the zone is bound to
      another key; state should be purged the same way, or deletion should say plainly that it is
      not. Positive finding alongside it: the tenant credential **is** correctly scoped — listing
      the broader `tenants/` prefix is refused with 403.
- [ ] **A tenant's MinIO state credentials are only recoverable from inside the state they
      unlock.** `terraform output` reads through the configured backend, so reading
      `state_backend` needs the keys it contains. Today the only way back in is the
      pre-migration `terraform.tfstate.backup` left in the tenant directory — which `.gitignore`
      treats as disposable. Losing it makes the tenant unreachable through its own Terraform,
      with a rebuild as the recovery. The API issues secrets in create responses only, by design,
      so the fix is not a read-back endpoint; it needs a deliberate custody answer. (The API
      token itself is fine — it is a normal output, recoverable once the backend opens.)
- [ ] The API's test suite asserts what the API writes, not what a workload can do. The
      regression test added here is the first of the latter kind; look for the same gap elsewhere.
