---
title: "OpenBao Drills"
weight: 20
aliases:
  - /docs/runbook/recovery/substrate-secrets-drills/
---

# OpenBao Drills

Two exercises, and they prove different things. The Transit half of the key-change drill and the
snapshot restore were written from a run against the live mobile site on 2026-09-17; the issuer half
from [CHG-0031](/docs/changes/2026/0031-site-root-ca/)'s. Every command below is one that was actually
issued.

| Drill | What changes | What it proves | Destructive? |
|---|---|---|---|
| **Key change** | a new PKI intermediate and a new Transit key version | the site survives keys it has never seen before | No — every step reverses |
| **Snapshot restore** | the instance is replaced and its data restored | the data survives at all ([ADR-0014](/docs/architecture/decisions/tenant-model/0014-tenant-state-durability/)) | Yes, on a scratch instance |

**Why both.** A snapshot restore brings back the *same* issuer and the *same* Transit key, so nothing
about a changed key is exercised — a certificate still verifies and a stored secret still decrypts.
The three defects [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) found were all in the
*key change* path, and none of them would have appeared in a restore.

---

## Why the key-change drill matters

Everything it exercises is a thing that happens for real: an OpenBao rebuilt after a loss, an
intermediate rotated before it expires, a Transit key rotated after a suspected exposure. Each leaves the site holding
credentials issued under something that no longer exists, and each of those paths had a defect in it
the first time it ran.

It is also the regression test for those three fixes. Run it after any change to the `openbao` or
`deevnet_api` roles, or to the API's store and TLS handling.

## Before starting

- **Both tenants' state to hand**, because the Transit half deliberately makes their stored secrets
  unreadable and they must resupply. `terraform show -json` from each tenant gives the values.
- **A token for OpenBao.** Log in as Ansible's AppRole from the inventory vault; do not use a root
  token, and there should not be one.
- Note the current state so the drill has a baseline: the serial of the certificate the API serves,
  and the Transit key's `latest_version` and `min_decryption_version`.

---

## Part 1 — the intermediate changes

OpenBao issues from an intermediate under the site root, which lives in the inventory
([ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/)). A rebuilt
OpenBao, or a rotation before the five years run out, replaces the intermediate and nothing else. The
drill is that rotation.

**Rotate the intermediate:**

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/openbao.yml -e openbao_pki_rotate_intermediate=true
```

**What must happen:**

1. `Sign an intermediate under the site root` runs: OpenBao generates a key and request, the control
   node signs it with the root, OpenBao installs it and makes it the default issuer.
2. `Check OpenBao now issues under the site root` passes.

**Then renew everything:**

```bash
ansible-playbook playbooks/certs.yml
```

3. **Nothing is reissued.** Every service's certificate was signed by the previous intermediate,
   which still chains to the root, and every client trusts only the root. `changed=0` apart from the
   login tasks is the pass.
4. **No client is handed anything.** Tenants, the egress agent, the log bridge and the Builder all
   hold the root, which did not change.

**Then force one reissue**, to prove a new certificate comes from the new intermediate:

```bash
ssh a_autoprov@dv02prv001v01 sudo rm /srv/deevnet-api/tls/api.pem
ansible-playbook playbooks/certs.yml --limit deevnet_api
```

5. `Restart now if the certificate or the environment changed` runs **before** the readiness wait.
   If it ran after, the wait would verify against a container still serving the old certificate,
   fail, and leave the handler unrun, so the next run would find nothing changed and fail the same
   way.
6. `openssl s_client -connect api.mobile.deevnet.net:8080 -showcerts` shows the new intermediate's
   serial, and verifies against the root.

**Verify:** `/readyz` answers `200` from the Builder against the root; one egress agent run
succeeds; every tenant's `terraform plan` is clean.

**To reverse:** nothing needs reversing. The new intermediate is a legitimate steady state. The
previous one stays in `pki/issuers` and can be made default again.

---

## Part 2 — the Transit key changes

**Rotate, then forbid the old version.** Rotation alone proves nothing: old ciphertext still decrypts
under its own version. Raising `min_decryption_version` is what makes the stored secrets unreadable.

```bash
curl --cacert <listener.pem> -H "X-Vault-Token: $TOK" -X POST \
  https://<openbao>:8200/v1/transit/keys/tenant-secrets/rotate

curl --cacert <listener.pem> -H "X-Vault-Token: $TOK" -X POST \
  https://<openbao>:8200/v1/transit/keys/tenant-secrets/config \
  -d '{"min_decryption_version":2}'
```

**What must happen:**

1. **A tenant still authenticates.** `terraform plan` succeeds. This is the whole point: the token's
   MAC is verified without the registry and the token hash is not sealed, so an unreadable secret must
   not make the tenant unauthenticatable. Before this was fixed, every call answered `401` and the
   documented recovery was unreachable.
2. **The API says so plainly.** `podman logs deevnet-api` carries
   `stored secret will not open; it must be supplied again`, once per secret, with OpenBao's own reason
   (`ciphertext or signature version is disallowed by policy (too old)`).
3. **The tenant read says so, and a plan notices.** `secrets_stored` goes false, and the tenant's next
   `terraform plan` shows **one in-place change** on the tenant resource: the three secrets and the flag.
   Everything else is untouched — index, subnet, zones, gateway — because the registry row is still
   there and only the secrets are unreadable:

   ```text
   ~ resource "deevnet_tenant" "this" {
       ~ api_token        = (sensitive value)
       ~ secrets_stored   = false -> (known after apply)
       ~ state_secret_key = (sensitive value)
       ~ tsig_secret      = (sensitive value)
         # (18 unchanged attributes hidden)
     }
   Plan: 0 to add, 1 to change, 0 to destroy.
   ```

4. **`terraform apply` reseals it.** The tenant sends the copies from its own state, which are the
   authoritative ones
   ([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §4). No operator call
   is needed: the resupply is an ordinary apply, on each tenant.

**Verify:** the stored columns carry the new key version, and `secrets_stored` is true again.

```sql
SELECT name, left(tsig_secret,10), left(state_secret,10) FROM tenants ORDER BY idx;
```

**To reverse:** set `min_decryption_version` back to `1`. It is harmless once everything is resealed,
and it leaves the older key version readable for anything missed.

---

## Finish

Also check the build path still works: `eval "$(make -s -C deevnet-image-factory pve2-env)"` exits 0
and prints the exports. It logs in as the image-factory AppRole and reads
`image-factory/proxmox/<node>` ([Build-Time Secrets](/docs/runbook/substrate/building-recovery/build-secrets/)).

Both plays `changed=0`, `/readyz` `200`, every tenant name resolving forward, every reverse record
naming its workload, and both tenants' plans clean.

**A tenant learns this by itself.** `secrets_stored` on the tenant read was added after the first run
of this drill, precisely because the resupply had been a `curl` call an operator had to remember. Both
halves of the drill are now ordinary role runs and ordinary applies.

**Older stored ciphertext stays readable** once `min_decryption_version` is set back, so setting it
back is safe and is the last step. Nothing should still need it — both tenants resealed — but a tenant
that was not applied during the drill would.

---

## Snapshot restore

Still unproven, and it is [ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/)'s
last unconfirmed claim. The shape: take a Raft snapshot, stand up a fresh instance with **the same
seal key** from the vault, restore into it, and confirm KV, Transit and PKI come back and the API
decrypts its stored secrets. Run it on a scratch instance rather than the live one — the seal key is
what makes a copy of the data readable, so a restored snapshot elsewhere is a full copy of every secret
and is treated as such.
