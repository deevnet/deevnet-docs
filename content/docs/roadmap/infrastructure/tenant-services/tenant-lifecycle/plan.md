---
title: "Tenant Lifecycle: Project Plan"
linkTitle: "Project Plan"
weight: 1
tasks_completed: 9
tasks_in_progress: 2
tasks_planned: 4
---

# Tenant Lifecycle: Project Plan

A repeatable, code-defined tenant lifecycle: each tenant is an isolated workload that supplies its own IaC/CaC to rebuild from scratch against the substrate, one of three plans for the tenant platform with [Tenant Fabric](/docs/roadmap/infrastructure/tenant-services/tenant-fabric/plan/) and [Tenant Platform Services](/docs/roadmap/infrastructure/tenant-services/platform-services/plan/).

**Roadmap item:** [Tenant Lifecycle](/docs/roadmap/infrastructure/tenant-services/tenant-lifecycle/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Define tenant contracts 🔄

The interface every tenant must satisfy to be rebuildable against the substrate.

**In practice, the contract is now the Deevnet API and its Terraform provider**
([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/), deployed by
[CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/)). A tenant is admitted with a single-use
enrollment token, then declares itself, its workloads and its names through one provider. It holds
no Proxmox credential, no vault access and no index. What it may consume is
[ADR-0010](/docs/architecture/decisions/tenant-model/0010-tenants-consume-platform-services/)'s, and the tenant
runbook describes each service. What is still missing is the boundary written down as one
specification.

- What a tenant **supplies** as code: network attachment, DNS records, compute/resource
  declaration, naming.
- What the substrate **guarantees** in return: a network to attach to, a perimeter, and a DNS
  zone to publish into.
- The tenant↔substrate boundary written as a specification, so any conforming tenant can be built.

---

## Tenant provisioning tooling 🔄

A repeatable, code-defined tenant lifecycle.

- ✅ Reusable Terraform (`bpg/proxmox`) module implementing the network and compute halves of the
  tenant contract: VRF + VNet(s) + subnet + VMs from template, addressed by cloud-init.
- ✅ One tenant = one instantiation, **in its own repository** (`deevnet-tenant-<name>`), consuming
  the module by git tag and a fabric attachment the substrate issues at onboarding (ADR-0006).
  Create, rebuild and destroy from code, with every identifier derived from one allocated index.
- ✅ A reference implementation new tenants are copied from, which **cannot itself be applied** —
  it ships with an index the module rejects, so the guard does not depend on being read.
- ✅ DNS publication over RFC 2136 with a per-zone TSIG key (ADR-0004), and a state store tenants
  may use or decline (ADR-0007).
- ✅ Record the Deevnet API's Proxmox access: `DeevnetTenantBuilder`, `DeevnetNodeAudit`, the user
  and ACLs are declared in inventory and recreated by `deevnet.builder`'s `proxmox_node_access` role
  (2026-09-27)
- ⏳ Remove the unused `TerraformProv` role on `dv02hyp002p02`, left from the retired tenant-module
  flow; no ACL references it
- ⏳ Exercise tenant credential recovery end to end: a tenant that has lost its state-store keys gets
  back in through an operator reconcile
  ([Lost State or Credentials](/docs/runbook/tenant/recovery/lost-credentials/)), proven on `tdemo`
- ⏳ Bring the Deevnet API's README up to date: its route table (Wi-Fi keys, devices and broker
  accounts are live, not `501`) and its OpenBao field list (`broker_writer_key`, `log_writer_key`,
  `grafana_admin_password`)

---

## First tenant — end-to-end 🔄

Prove the whole path with a real tenant.

- ✅ Provisioned from code: `tdemo` (index 1, `10.20.129.0/24`), cloud-init addressed.
- ✅ Egress via the perimeter, verified from inside the workload rather than from a NAT counter —
  and verified *not* to reach the management segment on-link.
- ✅ DNS publication end to end: `dig @10.20.99.1 tdemo-1.tdemo.mobile.deevnet.net` answers
  `10.20.129.10`, and the reverse answers the name — records written by the tenant's own Terraform
  over TSIG-signed RFC 2136, served by substrate-run PowerDNS, reached through the resolver's
  forward.
- ✅ Moved to its own repository with an empty plan as the acceptance gate: same state, same
  resource addresses, same running VM, same records, zero API mutations.
- 🔄 Inter-tenant isolation. There are now three tenants (`tdemo`, `eds`, `mabell`), and every
  platform service's isolation is **measured**: state (a credential is refused for another tenant's
  prefix), devices (`404` for another tenant's,
  [CHG-0014](/docs/changes/2026/0014-tenant-device-registry/)), broker topics
  ([CHG-0016](/docs/changes/2026/0016-broker-accounts/)), logs in both directions
  ([CHG-0020](/docs/changes/2026/0020-tenant-log-tokens/)) and dashboards
  ([CHG-0024](/docs/changes/2026/0024-tenant-dashboards/)). Still untested: network isolation
  between two tenants' workloads.
- ⏳ Rebuild-from-scratch drill — now re-scoped to the reference implementation: create a throwaway
  tenant repository from the reference tenant, `deevnet-tenant-tdemo`, apply, verify, destroy. Run at each module MAJOR tag.
