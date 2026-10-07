---
title: "CHG-0038: The Reconcile Restores Everything"
weight: -38
---

# CHG-0038: The Reconcile Restores Everything

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. One API deploy; one router change; one Grafana change |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API), `dv02cor002p01` (an API user), `dv02obs001v01` (a Grafana login); the provider |
| **Automation** | `deevnet-provisioning-api` (tag and stage), `terraform-provider-deevnet` (tag and publish), `deevnet.mgmt` `site.yml --tags deevnet-api,grafana`, `deevnet.net` for the OPNsense user, `make reconcile` |
| **Risk** | Medium. Most likely to go wrong: a reconcile that rewrites a backend a tenant has since changed. The reconcile writes only what the registry holds, which is what the tenant last applied |
| **Related changes** | [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/), [CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/) |
| **Related incidents** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) |
| **Related runbooks** | [Recovery](/docs/runbook/substrate/recovery/), [After a Site Rebuild](/docs/runbook/tenant/recovery/after-a-site-rebuild/), [Lost State or Credentials](/docs/runbook/tenant/recovery/lost-credentials/) |

---

## Summary

A reconcile re-ensures six things for a tenant today: its zone and key, the router's forwarding, its
state user, its network, its log users and its Grafana organization. After a backend is rebuilt, a
tenant's workloads, DNS records, Wi-Fi keys and broker accounts don't come back, and its own plain
apply sees no change. This change makes one operator command put back **everything the registry
holds**, with the same secrets. It fixes the edges of an OpenBao rebuild found by the review, adds an
operator reissue for a lost state secret, and gives the API its own credentials on the router and in
Grafana ([2026-10 review: T1, T5, T2, A6, A7](/docs/architecture/reviews/2026-10-rebuild-and-access/#t1-reconcile-coverage)).

## Goal

- `make reconcile --all` after any runtime-service rebuild restores, for every tenant:
  - **workloads** missing from the hypervisor, cloned again with the same VMID, MAC, address, name and
    SSH keys (the tenant pushes its application again);
  - **DNS records**;
  - **Wi-Fi keys and broker accounts**, with the same secrets, from the API's stored copies.
- A stored copy that can't be read is skipped and reported, never written empty.
- A restore returns what it re-mints; `make reconcile` shows new log tokens instead of discarding them;
  the provider accepts a changed dashboard password.
- An operator target reissues a tenant's state secret: a new secret, the store's user updated, handed
  over like an enrollment token.
- The API writes to the router with its own OPNsense user, limited to the resolver's settings and
  the DHCP server's reservations ([CHG-0044](/docs/changes/2026/0044-tenant-device-addresses/)), and to
  Grafana with its own server-admin login.
- The integration tests include an "OpenBao rebuilt" case and a "backend rebuilt" case.
- The recovery chart's "doesn't come back on its own" column shrinks to what only tenants can restore.

## Scope

**In scope:** the API's reconcile and restore, the provider's tenant resource, the operator scripts,
the API's router and Grafana credentials, reading the API's secrets from files (opportunistic).
**Out of scope:** device secrets in tenant code (CHG-0040); token reissue and revocation (deferred,
[T4](/docs/architecture/reviews/2026-10-rebuild-and-access/#t4-tenant-tokens)).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Re-cloning a workload that exists but didn't answer | the tenant hypervisor | Clone only when Proxmox reports the VMID absent, never on a failed call |
| A reconcile overwrites a Wi-Fi key with a stale copy | the controller | The registry's copy is what the tenant last applied; the tenant's next apply wins if they differ |
| The API's narrowed router user lacks a privilege | the router | Prove it against the router before removing the shared key from the API |
| A provider change breaks tenants' plans | tenants | Release as a minor version; tenants on `~> 0.5` take it; test against tdemo first |

## Prerequisites

- [ ] Vault decrypted; collections built
- [ ] Integration test environment (PostgreSQL, PowerDNS, MinIO, Grafana containers) working
- [ ] tdemo applied and clean, as the first test tenant

## Procedure

### Step 1: The API, built and tested off the site

Reconcile steps for workloads, records, Wi-Fi keys and broker accounts; the unreadable guard; restore
returning re-minted tokens; the state-secret reissue route; reading secrets from `*_FILE`. Integration
tests for each, including an OpenBao rebuild.

**Verify:** `make test-integration` passes.

### Step 2: The provider

The tenant resource expects a changed dashboard password. Tag and publish to the downloads site.

**Verify:** a tenant plan against the new API is clean.

### Step 3: The API's own credentials

An OPNsense user for the API, in a group limited to the resolver's settings; a Grafana server-admin
login for the API. Both vaulted, and their rotation documented.

**Verify:** the API writes a forward and creates an organization with its own credentials; it can no
longer change a firewall rule.

### Step 4: Deploy and reconcile

Stage and deploy the API; `make reconcile --all`.

**Verify:** every tenant reconciles `ok`; with a workload deliberately deleted from Proxmox (tdemo's),
the reconcile clones it again at the same address.

### Step 5: The docs

Update the recovery chart, *After a Site Rebuild*, *Lost State or Credentials* (the reissue), the
Deevnet API page, and *Verify Site*.

## Verification

After any runtime service is rebuilt, one `make reconcile --all` restores every tenant's
infrastructure, with no tenant action beyond pushing applications to re-cloned workloads.

## Undo

Redeploy the previous API version and provider; the API's old shared credentials stay in the vault
until this change is verified.

## To discover

- Whether the controller and broker backends answer "absent" distinctly from "unreachable".
- OPNsense's privilege names for the resolver's pages, and for the DHCP server's reservations, from
  its current documentation.
- Whether tdemo's workload re-clones with the same ordinal in practice.
