---
title: "ADR-0034: Tenants Deliver Their Own Code"
weight: -34
---

# ADR-0034: Tenants Deliver Their Own Code, and Deliver It Again

|  |  |
|--|--|
| **Status** | Accepted (2026-10-05): already how the platform works. [CHG-0028](/docs/changes/2026/0028-tenant-workload-login/) gave tenants their own login on their workloads, and `eds` runs its services this way (since 2026-09-28) |
| **Date** | 2026-10-05 |
| **Scope** | How a tenant's application code and settings reach its workloads, and how they come back after a workload is lost. Not how the workload itself is built ([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/)), and not how a tenant logs in ([ADR-0028](/docs/architecture/decisions/tenant-model/0028-tenant-workload-login/)). |
| **Supersedes** | [ADR-0017: How Tenant Code Reaches a Tenant Workload](/docs/architecture/decisions/tenant-model/0017-tenant-code-delivery/), whole |
| **Related** | [ADR-0010: Tenants Consume Platform Services](/docs/architecture/decisions/tenant-model/0010-tenants-consume-platform-services/), [ADR-0018: Operator Access to Tenant Workloads](/docs/architecture/decisions/tenant-networking/0018-operator-access-to-tenants/), [ADR-0021: Tenant Secrets](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/) (depended on ADR-0017; to be revisited), [ADR-0033: Code Is the State](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/) |

---

## Context

**ADR-0017 planned an unattended pull.** A tenant would declare its workload's configuration to the
API in a Deevnet schema, and an agent in the workload would fetch it at first boot through an SMBIOS
pointer. It forbade any push. None of it was built.

**Tenants ship anyway, by pushing.** ADR-0028 gave each tenant a login on its own workloads, with
its own key and sudo. The tenant guide's
[Deploy Your App](/docs/runbook/tenant/deploy-your-app/) builds a container image on the tenant's
computer, copies it over SSH, and runs it under systemd with the tenant's `kit.env`. `eds` deploys
its two services this way with one `make deploy`, kept in its own repository.

**This site is a mobile IoT lab, not production.** There is one site. A workload lost in a rebuild
costs its tenant a redeploy and some downtime, not a customer.

---

## Decision

### 1. The tenant pushes its code

- **From its own computer or CI, over SSH, with whatever tools it likes.** The guide's pattern is
  an image copied with `podman save | ssh … podman load`, settings in `kit.env`, and a systemd
  unit. No registry and no operator are involved.
- **The substrate never delivers tenant code.** It builds the workload; what runs on it is the
  tenant's (ADR-0018: operator access is for operating a machine, not for delivering to it).

### 2. A lost workload is the tenant's to fill again

- **A replaced or rebuilt workload comes back empty, and the tenant pushes again.** The deploy
  steps belong in the tenant's repository, so pushing again is one command, and the tenant's code
  stays its state (ADR-0033).
- **A tenant that needs more availability than one site gives** deploys to more than one place,
  as it would on any platform.

### 3. No unattended delivery

There is no configuration schema, no agent in the workload, and no fetch at boot. A workload is the
template and nothing more until its tenant pushes.

---

## Consequences

**Workloads stay plain.** The template carries no Deevnet agent, and the Deevnet API is never in a
workload's boot path, so ADR-0012's provisioning-only stance holds with nothing to guard it.

**After a site rebuild, tenant applications are down until each tenant pushes again.** The tenant
runbook says so, and that is accepted for this site.

**Secrets reach a workload the same way as code**, in the files the tenant pushes. ADR-0021
planned to hand each workload a credential through ADR-0017's channel, and said it *"depends on
ADR-0017 being built"*. It is revisited separately.

---

## Alternatives considered

- **ADR-0017's pull: a Deevnet schema, an SMBIOS pointer and an agent.** Not pursued: it adds a
  tenant-facing schema to version, an agent to maintain in the template, and the API to a
  workload's boot path, to save a tenant one command on a site where the tenant is present.
- **cloud-init user-data supplied by the tenant.** Rejected, as ADR-0017 rejected it: it puts a
  hypervisor mechanism into the tenant contract.
- **The substrate pushes tenant code with its own automation.** Rejected: the substrate operates
  workloads, it doesn't own what runs on them (ADR-0018).

---

## Current state

- **Accepted, and in use.** `eds` runs palette and lightd on its `services` workload, deployed with
  `make deploy` from its repository.
- The template is plain Fedora with Podman; tenants log in as `tenant` with the keys they declare in
  `ssh_keys`.
