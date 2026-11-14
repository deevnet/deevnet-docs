---
title: "CHG-0067: Tenant Secrets in Their Own OpenBao Namespace"
weight: -67
---

# CHG-0067: Tenant Secrets in Their Own OpenBao Namespace

| | |
|---|---|
| **Date** | 2026-11-14 |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | **Complete.** API v0.22.4 and provider v0.10.1 deployed: a tenant's runtime secrets live in its own OpenBao namespace, proven on a throwaway tenant and, through OpenBao Agent, on the reference tenant's backend workload |
| **Window** | OpenBao work sessions. The OpenBao configuration adds a namespace and a policy without a restart; the API deploys restart only the API |
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
  and nothing else, from inside the tenant fabric only.
- A new value and an apply reach the workload without a replace or a push.
- Deleting a reader stops the workload's next login.
- After the namespace is lost, a reconcile and one apply bring everything back, with no secret lost.
- A tenant delete removes the tenant's namespace.
- Every read is in OpenBao's audit log.

## Scope

**In scope:** OpenBao's `tenants` namespace; the API's OpenBao policy; the API's
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
| A leaked reader credential is used elsewhere | OpenBao | The secret ID and its tokens are bound to the address OpenBao sees: the fabric's exit node at mobile, which source-NATs every workload. Inside the fabric, the reader's delete is what stops it |
| A held token outlives its reader's delete | OpenBao | Deleting an AppRole stops new logins but not a token already issued. A reader delete removes the AppRole and its policy together, which cuts the token off at once |

## Prerequisites

- [ ] OpenBao open (a work session) for every OpenBao change, API deploy and live test
- [ ] Vault decrypted; collections built
- [x] OpenBao 2.6.2's namespace policy paths proven on a local dev server (see below)

## Proven before building

**The policy shape was proven on 2026-11-14, on a throwaway OpenBao 2.6.2 dev server on the
Builder.** The server was local and was stopped afterwards; the site's OpenBao was not touched.

- **Child paths from the root.** A root-namespace policy reaches a tenant's namespace by prefixing
  its path: `tenants/sys/namespaces/*` to create and delete tenant namespaces, and
  `tenants/+/sys/mounts/*`, `tenants/+/secrets/data/*` and the like inside each one.
- **The API's grants stop at `tenants/`.** With that policy, the API created two tenant namespaces,
  their mounts, a policy and an AppRole in each, and wrote a secret. It was refused (`403`) reading
  a secret's value, reading the root's `deevnet-api/` mount, enabling a mount at the root and
  deleting `tenants` itself.
- **Tenants are isolated.** A workload token from `tenants/t1` was refused in `tenants/t2` both by
  header and by path prefix, and `t1`'s credential could not log in to `t2`. It could not read a
  path in its own namespace that its policy did not name, or write anything.
- **The secret ID is reusable and bound.** Two logins with the same secret ID succeeded from the
  bound address, and a login from another address was refused by the CIDR binding.
- **Rotation needs no new login.** A new version written by the API was read with the token the
  workload already held.
- **Revocation needs the policy deleted too.** After its AppRole was deleted, the workload could not
  log in, but its held token still read the secret. Deleting the reader's policy as well made the
  same token's next read `403`.
- **Deleting a namespace removes what is in it.** The delete returned `in-progress` and finished
  within seconds. The deleted namespace's workload token was refused, and a namespace made again
  under the same name held no mount or AppRole from before.

## Procedure

| Step | What | Check |
|---|---|---|
| 1 | The `openbao` role creates the `tenants` namespace; `--limit dv02idn001v01` | `sys/namespaces` lists `tenants/` |
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
- A login with the reader's credential from outside the tenant fabric is refused.

**Loss of the namespace, inside the tenant only:** with `tenants/tdemo` deleted by hand, a reconcile
makes it again, `terraform apply` writes the secrets and a new reader credential, and a push brings
the workload back with no replace.

**Removal:** a throwaway tenant's delete leaves no `tenants/<name>` namespace.

**Audit:** the workload's reads are in the audit log.

## Outcome

**Tenants can keep runtime secrets in their own OpenBao namespace, and every property the change
set out to prove held live, on a throwaway tenant, `tsec`, with a workload of its own.** The
namespace and the API's grants were applied on `dv02idn001v01`; API v0.22.0, then v0.22.1, was
deployed on `dv02prv001v01`; provider v0.10.0 was released and served in the tenant downloads.

| Check | Result |
|---|---|
| Value in plan or state | Neither secret's value in `terraform.tfstate` or in `terraform show -json` of a plan; a second plan showed no changes |
| Workload reads its secret | Login `200` from the workload, twice with the same secret ID; its assigned path read `200` |
| Isolation | With that token: a path not given `403`, a write `403`, `tenants/tdemo` `403`, the root's `deevnet-api/` `403`; the credential could not log in to `tenants/tdemo` |
| Address binding | A login from the Builder (`10.20.99.95`) refused by the CIDR binding |
| Rotation | A new value and `data_wo_version = 2`: the token the workload already held read version 2, with no new login, push or replace |
| Revocation | Deleting the reader: the held token's next read `403`, a new login refused |
| Recovery | With the secret and the reader deleted through the API, the plan showed both to create; one apply and one push, and the workload read again |
| Audit | Every read and write in `tenants/tsec/` in OpenBao's audit log, the workload's from the exit node and the API's from `10.20.25.20`, refusals included |
| Removal | `make remove-tenant NAME=tsec` deleted `tenants/tsec` (in the audit log); the old reader then got `namespace not found` |
| OpenBao Agent on a live workload | tdemo's backend, Fedora 44 with the `openbao` package: `scripts/run-with-secrets.sh` logged in, put the key in the app's environment and started it; a new value and `weather_api_key_version = 2` restarted the app with it at the next render, 2 minutes 20 seconds later, with no push. With the reader deleted, the agent's reads were refused |

The namespace loss was checked through the API's deletes, not by deleting `tenants/tsec` itself:
neither Ansible's nor the API's grants may delete a tenant's namespace outside a tenant delete, and
nothing was granted for the drill. The reconcile that makes a namespace is the one that made
`tenants/tdemo`.

## Departures from the plan

**The first live login from a workload was refused, because the tenant fabric source-NATs.**
- The reader was bound to its workload's address, `10.20.133.10/32` on the throwaway tenant
  `tsec`. OpenBao refused the login: *source address "10.20.50.22" unauthorized by CIDR
  restrictions on the role*.
- `10.20.50.22` is the fabric exit node, `dv02hyp002p02`, on tenant transit. It source-NATs
  everything leaving the fabric, so OpenBao sees that one address for every workload of every
  tenant. The dev server could not show this: it had no fabric in front of it.
- **Readers are now bound to the exit node** (API v0.22.1, `DEEVNET_TENANT_SECRETS_SOURCE_CIDRS`).
  A leaked credential works only from inside the fabric, from any tenant's workload. Inside it,
  the reader's delete is what stops one.
- With the login refused, the workload had no token, so the reads it tried that day prove
  nothing about isolation. They are run again once readers are rebound.

**Bringing tdemo up to the reference configuration found four faults, fixed on the way.**
- tdemo predates the log store and dashboards, so its state never held their credentials, and the
  reference `kit_env` failed to plan. Provider v0.10.1 plans a restore when the site has a service
  but state has no credential for it.
- A name deleted once and admitted again refused every restore, the live tenant's own token
  included (API v0.22.2).
- A restore returned no log tokens (API v0.22.3), and rotated the stored log tokens and dashboard
  password on every run (API v0.22.4).
- That first restore put back the state secret held in tdemo's Terraform state, undoing its
  CHG-0060 reissue: tdemo's state could not be saved until `.backend.env` was given the restored
  secret and the state was pushed. Only tdemo has ever had a reissue, so no other tenant was
  exposed.

## Follow-ups

- **A restore must not undo a state-secret reissue: done 2026-11-14.** A reissue changed the store
  and the tenant's `.backend.env`, but not the copy in its Terraform state, which a restore sent
  back and which won. API v0.22.5 marks a reissue and keeps the reissued secret over the older copy,
  returning it; provider v0.10.2 takes it into state. Proven live on tdemo: a restore sending the
  old secret got the reissued one back, and the store kept refusing the old one
  ([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §5).
- **The agent keeps retrying a revoked reader.** Its reads are refused, but the app it runs keeps
  the value it was started with until the agent gives up or is stopped. Deleting the workload, or
  stopping the app, is what ends it.

- **Per-workload binding:** exempt tenant traffic bound for the platform zone from the exit node's
  source NAT, so OpenBao sees each workload's own address, then unset the source CIDRs. It changes
  the tenant hypervisor's fabric and the core router's zone rules, so it is a change of its own.

## To close

**What is left before this change closes, from its procedure and verification.**

- [x] Step 1: the `tenants` namespace applied (`deevnet.mgmt` pull request 120, then the inventory's pull request 108)
- [x] Step 2: the API's policy widened, its live text identical to the policy proven refused at the root (`deevnet.mgmt` pull request 120)
- [x] Step 3: API v0.22.0 merged, released and deployed; a reconcile makes the namespace (API pull request 64)
- [x] Step 4: provider v0.10.0 released and mirrored in the tenant downloads (provider pull request 29)
- [x] API v0.22.1 deployed with readers bound to the fabric exit node
- [x] Step 5: the reference tenant's example merged (`deevnet-tenant-tdemo` pull request 17), its runner proven against OpenBao 2.6.2
- [x] OpenBao Agent reads a secret on a live workload, with `bao` installed there: tdemo's backend, 2026-11-14
- [x] Step 6: the docs: the tenant guide's Runtime Secrets page, the tenant contract, Shared Services, and the API's and provider's pages
- [x] Verification: isolation, rotation, revocation, address binding, recovery, removal and audit, all proven live
