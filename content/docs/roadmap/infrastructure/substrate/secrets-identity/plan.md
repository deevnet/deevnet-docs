---
title: "Secrets and Identity: Project Plan"
linkTitle: "Project Plan"
weight: 1
tasks_completed: 3
tasks_in_progress: 2
tasks_planned: 4
---

# Secrets and Identity: Project Plan

Secrets and identity services for the mobile site, one of three plans with the [Extended Management Plane](/docs/roadmap/infrastructure/substrate/management-plane/plan/) and [Observability](/docs/roadmap/infrastructure/substrate/observability/plan/).

- **GitHub:** https://github.com/deevnet/ansible-collection-deevnet.mgmt
- **Documentation:** https://deevnet.github.io/deevnet-docs/

**Roadmap item:** [Secrets and Identity](/docs/roadmap/infrastructure/substrate/secrets-identity/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

**In Scope**
- Secrets management
- Identity and access management

**Out of Scope**
- External identity federation (future phase)

---

## Secrets Management 🔄

OpenBao on `dv02idn001v01`, unsealed by a key ansible-vault delivers, which stays the root of trust
([ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/)).

- ✅ Migrate IaC secrets from env var lookups to Ansible Vault in inventory
- ✅ Evaluate dedicated secrets solutions: OpenBao
  ([ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/))
- ✅ Deploy secrets management service ([CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/))
- 🔄 Integrate consumers: the Deevnet API reads its backend credentials at start
  ([CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/)), and image-factory and tenant-fabric
  builds fetch the Proxmox token per run, with nothing on the Builder's disk
  ([CHG-0026](/docs/changes/2026/0026-build-secrets/)). Ansible administers OpenBao through its own
  AppRole, but most playbook secrets are still read from ansible-vault in inventory
- ⏳ Define secrets rotation policies ([Credential Rotation](/docs/roadmap/infrastructure/substrate/credential-rotation/))

---

## Identity Management 🔄

- 🔄 Evaluate identity solutions: Keycloak, with a realm per tenant, proposed in
  [ADR-0025](/docs/architecture/decisions/platform-services/0025-identity-directory/)
- ⏳ Deploy identity provider
- ⏳ Configure SSO for infrastructure services
- ⏳ Define RBAC policies
