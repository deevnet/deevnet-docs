---
title: "CHG-0067: Tenant Secrets in Their Own OpenBao Namespace"
weight: -67
---

# CHG-0067: Tenant Secrets in Their Own OpenBao Namespace

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | OpenBao work sessions. The OpenBao configuration adds an audit device and a namespace without a restart; the API deploys restart only the API |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao); `dv02prv001v01` (the Deevnet API) |
| **Automation** | `deevnet.mgmt` `openbao` role (`playbooks/openbao.yml`) and `site.yml --tags deevnet-api`, against `ansible-inventory-deevnet/mobile`; `deevnet-provisioning-api` v0.22.0; `terraform-provider-deevnet` v0.10.0; `deevnet-tenant-tdemo` |
| **Risk** | Medium. Most likely to go wrong: the API's wider OpenBao policy reaching beyond `tenants/`. It is granted only paths under the `tenants` namespace, and a test proves it refused at the root's `deevnet-api/` mount |
| **Related changes** | [CHG-0065](/docs/changes/2026/0065-tenant-removal-leftovers/) (what a tenant delete removes) |
| **Related incidents** | None |
| **Related runbooks** | None yet; the tenant guide gains a Secrets page |

---

## Summary

A tenant keeps its runtime secrets as code today: encrypted in its own repository and merged into
the settings it pushes to a workload ([ADR-0034](/docs/architecture/decisions/tenant-model/0034-tenants-deliver-their-own-code/)).
That works, but rotating a secret means pushing again to every workload that holds it, nothing can
revoke one workload's access, and nothing records which workload read what.

This change builds [ADR-0021](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/) as an
**optional** service. Each tenant gets a namespace, `tenants/<name>`, in the site's OpenBao. The
tenant writes its secrets there through the Deevnet API, from the copy in its repository. Each
workload reads only the paths its tenant assigned to it, under its own AppRole, with OpenBao Agent
running in the tenant's own code.

## Goal

- A tenant declares a secret with the provider. Its value appears in neither plan nor state.
- A tenant declares a reader for a workload, naming the paths it may read. The workload reads them,
  and nothing else, from its own address only.
- A new value and an apply reach the workload without a replace or a push.
- Deleting a reader stops the workload's next login.
- After the namespace is lost, a reconcile and one apply bring everything back, with no secret lost.
- A tenant delete removes the tenant's namespace.
- Every read is in OpenBao's audit log.

## Scope

**In scope:** OpenBao's audit device and `tenants` namespace; the API's OpenBao policy; the API's
secrets step and endpoints; the provider's `deevnet_secret` and `deevnet_secret_reader` resources;
an example in the reference tenant; the tenant guide.

**Out of scope:**
- Per-tenant PKI, dynamic secrets and tenant-enabled engines ([ADR-0021 §8](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/#8-not-now)).
- A Deevnet-built read agent. The tenant runs OpenBao Agent in its own code.
- Moving `eds` or `mabell` onto the service. The service is optional.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The API's policy reaches the substrate's own paths | OpenBao | Every new grant is under `tenants/`. A test reads the root's `deevnet-api/` mount through the new grants and must be refused |
| One tenant reaches another's namespace | OpenBao | Each call carries the caller's own namespace, derived from its token, never sent. A test uses tenant A's reader against tenant B's namespace |
| The API hands back a secret value | the API | The API's policy has no read on `secrets/data/`; a GET returns presence and version only |
| A leaked reader credential is used elsewhere | OpenBao | The secret ID and its tokens are bound to the workload's address |
| The audit device blocks OpenBao when its log cannot be written | OpenBao | The log goes to the VM's own disk with rotation; checked before the device is enabled |

## Prerequisites

- [ ] OpenBao open (a work session) for every OpenBao change, API deploy and live test
- [ ] Vault decrypted; collections built
- [ ] OpenBao 2.6.2's namespace policy paths confirmed against its documentation

## Procedure

| Step | What | Check |
|---|---|---|
| 1 | The `openbao` role enables a file audit device and creates the `tenants` namespace; `--limit dv02idn001v01` | `sys/audit` lists the device; `sys/namespaces` lists `tenants/` |
| 2 | The `deevnet-api` policy gains namespace administration under `tenants/` | The policy as loaded; a read of `deevnet-api/` through the new grants is refused |
| 3 | API v0.22.0: the secrets step, the secret and reader endpoints, the namespace removed on delete; `site.yml --tags deevnet-api` | Tests pass; live, a reconcile makes `tenants/tdemo` with its two mounts |
| 4 | Provider v0.10.0: `deevnet_secret` and `deevnet_secret_reader` | Plan and state hold no value; a new version writes again |
| 5 | The reference tenant: a secret, a reader and an OpenBao Agent example | The backend workload renders the secret |
| 6 | The docs | The tenant guide, the architecture page, ADR-0021 and the roadmap match what is built |

**Rollback:** redeploy the previous API version and remove the new policy grants. Tenant namespaces
can stay or be deleted; every value in them is a copy.

## Verification

**Isolation:**
- A token from tenant A's namespace is refused in tenant B's.
- The API's policy reaches `tenants/*` and not the root's `deevnet-api/` mount.
- Deleting a namespace removes its AppRoles and secret IDs.

**On `tdemo`:**
- `terraform plan` and `terraform show -json` hold no secret value.
- OpenBao Agent on the backend workload renders the secret.
- A new value and an apply reach the workload with no replace.
- Deleting the reader makes the next login fail.
- A login with the reader's credential from another address is refused.

**Loss of the namespace, inside the tenant only:** with `tenants/tdemo` deleted by hand, a reconcile
makes it again, `terraform apply` writes the secrets and a new reader credential, and a push brings
the workload back with no replace.

**Removal:** a throwaway tenant's delete leaves no `tenants/<name>` namespace.

**Audit:** the workload's reads are in the audit log.

## To close

**What is left before this change closes, from its procedure and verification.**

- [ ] Step 1: the audit device and the `tenants` namespace applied
- [ ] Step 2: the API's policy widened and proven refused at the root
- [ ] Step 3: API v0.22.0 merged, released and deployed; a reconcile makes the namespace
- [ ] Step 4: provider v0.10.0 released and mirrored in the tenant downloads
- [ ] Step 5: the reference tenant reads its secret through OpenBao Agent
- [ ] Step 6: the docs
- [ ] Verification: isolation, rotation, revocation, address binding, loss of the namespace, removal and audit, all proven live
