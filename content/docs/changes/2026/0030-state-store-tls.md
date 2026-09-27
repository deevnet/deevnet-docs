---
title: "CHG-0030: The State Store Over TLS"
weight: -30
---

# CHG-0030: The State Store Over TLS

| | |
|---|---|
| **Date** | 2026-09-27 |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | In progress |
| **Window** | 2026-09-27, started 12:41 |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (MinIO, the Deevnet API), `dv02idn001v01` (OpenBao issues one certificate), the tdemo, eds and mabell backends |
| **Automation** | `deevnet.mgmt` `site.yml --tags tenant-state` and `--tags deevnet-api`, `--tags tenant-downloads`; `deevnet-provisioning-api` `make stage`; `terraform-provider-deevnet` `make stage`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium — every tenant backend and the API's admin client stop working at the moment MinIO switches, until each is pointed at `https` |
| **Related changes** | [CHG-0029](/docs/changes/2026/0029-tenant-developer-network-keys/), whose isolation needs this |
| **Related incidents** | [INC-0003](/docs/incidents/) (a rebuilt OpenBao's new root, which the reissue check covers) |
| **Related runbooks** | [State Store](/docs/runbook/tenant/services/state-store/) |

---

## Summary

The state store, MinIO on `dv02prv001v01`, is the last service a tenant reaches that is plain HTTP.
A tenant's Terraform state holds every secret the substrate issued it, and on `DVNTM-TD` it crosses
a segment whose client isolation stops IP but not ARP spoofing
([ADR-0029](/docs/architecture/decisions/tenant-networking/0029-tenant-developer-network-keys/) §4).
[ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) already says it
should be TLS.

After this change MinIO serves TLS on `:9000` with a certificate from the site CA:
- **Tenants** reach it at `https://tfstate.mobile.deevnet.net:9000`, verified with the
  `site-ca.pem` they already hold.
- **The Deevnet API** reaches it by address, verified with the CA it already mounts.
- **The role's own checks** reach it at `127.0.0.1`.

No client can skip verification.

## Goal

- `curl --cacert site-ca.pem https://tfstate.mobile.deevnet.net:9000/minio/health/live` answers
  `200` from `DVNTM-TD`. A plain `http://` request gets only Go's
  `400 Client sent an HTTP request to an HTTPS server`, and no data.
- The certificate names `tfstate.mobile.deevnet.net`, `dv02prv001v01.mobile.deevnet.net`, the host
  address and `127.0.0.1`, and is issued by the site CA.
- The API reports `v0.9.0` or later. A tenant create and delete (throwaway `tprobe`) succeed, which proves
  the admin client works over TLS.
- `terraform plan` works from tdemo, eds and mabell with the `https` endpoint and
  `custom_ca_bundle`.
- `deevnet_tenant.state_endpoint` reads `https://…` for every tenant.
- `tenant-check.sh` and `segment-check.sh` report the state store as **TLS verified**.

## Scope

**In scope:**
- MinIO's certificate and listener.
- The API's admin client (`MINIO_ADMIN_TLS`, `MINIO_ADMIN_CACERT`).
- The endpoint tenants are told.
- The three existing backends.
- The two check scripts, and the tenant state-store page.

**Out of scope:**
- MinIO's console on `:9001`. It is not reachable from any tenant segment. It gets TLS with the same
  certificate as a side effect, but is not verified here.
- Replacing MinIO ([ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/)).
- A second copy of the state ([ADR-0014](/docs/architecture/decisions/tenant-model/0014-tenant-state-durability/)).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Every backend and the API break together at the switch | prv | Steps 2 and 3 run back to back. The tenants' backends switch in step 4, and nothing is lost meanwhile: state stays in the bucket, and a failed `init` changes nothing |
| `mc` inside the container cannot verify the listener | prv | The container's `SSL_CERT_FILE` is the site CA, and `podman exec` inherits it. If it does not, the bucket step fails loudly and the role stops. That this holds is inferred from how podman behaves, not documented |
| The certificate goes stale when OpenBao is rebuilt | prv | The role compares the host's CA with OpenBao's on every run and reissues on a change (the INC-0003 lesson) |
| A tenant runs `init` without the CA | laptop | It fails with an x509 error, not silently; the tenant page says what to add |

## Prerequisites

- [ ] PRs merged: `deevnet-provisioning-api`, `terraform-provider-deevnet`,
      `ansible-collection-deevnet.mgmt`, `ansible-collection-deevnet.net` and
      `ansible-inventory-deevnet` (all `chg-0030-state-store-tls`). tdemo's `backend.tf` already
      names `https` and the site CA (the reference-tenant rework, `deevnet-tenant-tdemo` #7)
- [ ] Vault decrypted, collections built

## Procedure

### Step 1: Stage the API and provider

**One release carries all three changes.** The API and provider on `main` hold the code for
CHG-0028, CHG-0029 and CHG-0030 together, and each behavior is off until that change's own role or
inventory switch turns it on. So the first of the three to run tags and stages API `v0.9.0` and
provider `0.5.0`, and the others deploy that same release. If it is already staged, skip the tag.

**Run:**

```bash
cd deevnet-provisioning-api && git tag v0.9.0 && git push origin v0.9.0 && make stage   # unless staged
cd ../terraform-provider-deevnet && git tag v0.5.0 && git push origin v0.5.0 && make stage   # unless staged
```

**Verify:** both artifacts are on the Builder.

**Undo:** nothing to undo.

### Step 2: TLS on MinIO

**Run** (in `ansible-collection-deevnet.mgmt`):

```bash
ansible-playbook playbooks/site.yml --tags tenant-state --limit dv02prv001v01
```

**Verify:**

1. The role's own health check passes over `https://127.0.0.1:9000`, verified against the site CA.
2. `openssl s_client -connect tfstate.mobile.deevnet.net:9000 -CAfile site-ca.pem` gives
   `Verify return code: 0 (ok)`, and the SANs are the four in the Goal.
3. The bucket step's `mc alias set local https://127.0.0.1:9000` succeeds, which proves `mc` inside
   the container verifies.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: The API

**Run:**

```bash
ansible-playbook playbooks/site.yml --tags deevnet-api --limit dv02prv001v01
```

**Verify:** the API reports `v0.9.0` or later, and its environment has `MINIO_ADMIN_TLS=true`,
`MINIO_ADMIN_CACERT` and `DEEVNET_STATE_ENDPOINT=https://…`. Admit, create and delete `tprobe`.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: The tenants' backends

**Run:** in the eds and mabell repositories, change the backend's endpoint to
`https://tfstate.mobile.deevnet.net:9000` and add `custom_ca_bundle = "site-ca.pem"`. tdemo's
`backend.tf` already has both. Then, in all three:

```bash
terraform init -reconfigure
terraform plan
```

**Verify:** `init` succeeds against the same bucket and key, and `plan` shows only
`state_endpoint` changing to `https`.

**Undo:** none needed. A backend that has not switched just fails to `init` until it does.

### Step 5: Scripts, downloads, docs

**Run:** `ansible-playbook playbooks/site.yml --tags tenant-downloads --limit dv02obs001v01`
(the updated `tenant-check.sh`), then merge the docs PR for the tenant State Store page.

**Verify:** from `DVNTM-TD`, `tenant-check.sh` and `segment-check.sh` report the state store as TLS
verified.

## Verification

The Goal, as a whole, from a laptop on `DVNTM-TD`.

## Undo

### Undo Step 2

Set `minio_tls_enabled: false` in `group_vars/tenant_state/vars.yml` and run the role again. MinIO
serves plain HTTP again; the certificate files are left in place and ignored.

### Undo Step 3

Set `deevnet_api_minio_tls: false`, and set `deevnet_api_state_endpoint` back to `http://…`, then
deploy the API again.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] The console on `:9001`: decide whether it should be reachable at all.
