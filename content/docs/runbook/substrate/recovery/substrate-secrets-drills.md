---
title: "OpenBao Drills"
weight: 20
aliases:
  - /docs/runbook/recovery/substrate-secrets-drills/
---

# OpenBao Drills

Two exercises, and they prove different things. Both were written from a run against the live mobile
site on 2026-09-17; every command below is one that was actually issued.

| Drill | What changes | What it proves | Destructive? |
|---|---|---|---|
| **Key change** | a new PKI issuer and a new Transit key version | the site survives keys it has never seen before | No — every step reverses |
| **Snapshot restore** | the instance is replaced and its data restored | the data survives at all ([ADR-0014](/docs/architecture/decisions/0014-tenant-state-durability/)) | Yes, on a scratch instance |

**Why both.** A snapshot restore brings back the *same* issuer and the *same* Transit key, so nothing
about a changed key is exercised — a certificate still verifies and a stored secret still decrypts.
The three defects [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) found were all in the
*key change* path, and none of them would have appeared in a restore.

---

## Why the key-change drill matters

Everything it exercises is a thing that happens for real: an OpenBao rebuilt after a loss, a CA
rotated on schedule, a Transit key rotated after a suspected exposure. Each leaves the site holding
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

## Part 1 — the issuer changes

**Rotate the root and move the default.** The new issuer is what `pki/cert/ca` returns afterwards,
which is the condition the `deevnet_api` role compares against.

```bash
curl --cacert <listener.pem> -H "X-Vault-Token: $TOK" -X POST \
  https://<openbao>:8200/v1/pki/root/rotate/internal \
  -d '{"common_name":"Deevnet mobile internal CA","ttl":"87600h","issuer_name":"drill-rotated"}'

curl --cacert <listener.pem> -H "X-Vault-Token: $TOK" -X POST \
  https://<openbao>:8200/v1/pki/config/issuers \
  -d '{"default":"<new issuer_id>","default_follows_latest_issuer":false}'
```

**Then run the API role.** It must reissue, not skip.

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --limit dv02prv001v01 --skip-tags vms,tenant-state
```

**What must happen, in order:**

1. `Decide whether the certificate must be issued` resolves true. Expiry alone would not have caught
   this: the old certificate is still valid for its full term, and the new root carries the same common
   name. The role compares the CA the host holds against `pki/cert/ca`.
2. The certificate, key and site CA are written — three changed items.
3. `Restart now if the certificate or the environment changed` flushes the handler, and the restart
   runs **before** the readiness wait. If it runs after, the wait verifies a new CA against a container
   still serving the old certificate, fails, and aborts the play — which leaves the handler unrun, so
   the next run finds nothing changed and fails identically. That deadlock has to be broken by hand.
4. `Wait for the API to report ready` passes.

**Refresh the control node's copy**, which the `openbao` role fetches:

```bash
ansible-playbook playbooks/openbao.yml      # .openbao/site-ca.pem follows the rotation
```

**Redeliver the CA to everything that trusts it** — both tenant repositories and the egress agent.
Skip this and the agent stops being able to read the VRF list:

```bash
cp .openbao/site-ca.pem <each tenant repo>/site-ca.pem
cd ../ansible-collection-deevnet.net && ansible-playbook playbooks/tenant-egress-agent.yml
```

**Verify:** `/readyz` answers `200` from the Builder against the new CA and the served certificate's
serial has changed; one agent run succeeds and `frr.conf.local` still carries every tenant VRF; both
tenants' plans are clean.

**To reverse:** nothing needs reversing. The rotated issuer is a legitimate steady state, and moving
the default back would strand the certificate that was just issued from it. The previous issuer stays
in `pki/issuers` and can be made default again if that is ever wanted.

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
   ([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/) §4). No operator call
   is needed: the resupply is an ordinary apply, on each tenant.

**Verify:** the stored columns carry the new key version, and `secrets_stored` is true again.

```sql
SELECT name, left(tsig_secret,10), left(state_secret,10) FROM tenants ORDER BY idx;
```

**To reverse:** set `min_decryption_version` back to `1`. It is harmless once everything is resealed,
and it leaves the older key version readable for anything missed.

---

## Finish

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

Still unproven, and it is [ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/)'s
last unconfirmed claim. The shape: take a Raft snapshot, stand up a fresh instance with **the same
seal key** from the vault, restore into it, and confirm KV, Transit and PKI come back and the API
decrypts its stored secrets. Run it on a scratch instance rather than the live one — the seal key is
what makes a copy of the data readable, so a restored snapshot elsewhere is a full copy of every secret
and is treated as such.
