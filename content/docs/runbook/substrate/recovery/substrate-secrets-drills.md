---
title: "OpenBao Drills"
weight: 20
aliases:
  - /docs/runbook/recovery/substrate-secrets-drills/
---

# OpenBao Drills

**OpenBao is rebuilt from the vault, never restored**
([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/) §4).
Two drills prove it:

| Drill | What changes | What it proves | Destructive? |
|---|---|---|---|
| **Rebuild** | OpenBao's storage is set aside and the instance rebuilt from the vault | a lost OpenBao comes back with the same keys and the API reads every stored secret | Yes; reversible until its last step |
| **Key change** | the Transit key is replaced and every stored value resealed | the site survives a key it has never seen | No |

The key change is the procedure on [OpenBao's Keys](/docs/runbook/substrate/building-recovery/openbao-keys/#the-transit-key),
run as a drill. It was first run for real in [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/),
moving 26 stored values to a vault-held key.

**The rebuild drill has not been run yet.** It is CHG-0036's follow-up. The procedure below is
written from the role as it stands; correct it from the first run.

---

## Before the rebuild

**Tenant work through the API stops for the drill.** Devices and workloads keep running.

- The inventory decrypted (`make unvault`): the rebuild writes new values into it.
- A baseline, to compare after:
  - each tenant CA's fingerprint, from `pki-tenant-service/ca/pem` and `pki-tenant-device/ca/pem`;
  - every tenant reading back with `secrets_stored` true;
  - `eval "$(make -s -C deevnet-image-factory pve2-env)"` exiting 0.
- **Empty `vault_openbao_image_factory_role_id` and `_secret_id`** in `group_vars/all/vault.yml`. The
  role issues them only when they are empty, and the rebuilt OpenBao will not know the old ones.

## The rebuild

1. **Set the storage aside**, on `dv02idn001v01`. Moved, not deleted, so the drill can be undone:

   ```bash
   sudo systemctl stop openbao
   sudo mv /srv/openbao/data /srv/openbao/data.before-drill
   ```

2. **Run `ansible-playbook playbooks/openbao.yml`.** OpenBao starts empty and is initialized; the run
   imports both tenant CAs and the Transit key from the vault, writes the policies and AppRoles, and
   revokes the root token. It writes the new recovery key and Ansible's AppRole to
   `.openbao/dv02idn001v01-init.json`.
3. **Lock it in.** Move `vault_openbao_ansible_role_id`, `vault_openbao_ansible_secret_id` and the
   recovery key into the openbao vault; `make vault`, commit, push; then delete the file.
4. **Run `openbao.yml` again.** It logs in as Ansible, writes the build secrets, and issues the
   image-factory AppRole's credentials to `.openbao/image-factory-approle.json`. Move them into
   `group_vars/all/vault.yml`, `make vault`, commit, push, delete the file.
5. **Deploy the API** (`site.yml --tags deevnet-api --limit deevnet_api`). It writes its backend
   credentials into OpenBao's KV, and issues itself a secret ID, since the rebuilt OpenBao does not
   know its old one.

## Verify

- Both tenant CAs serve the baseline's fingerprints, and `playbooks/tenant-service-ca-verify.yml`
  passes.
- `transit/keys/<openbao_transit_key>` reports `imported_key: true`.
- **Every tenant reads back with `secrets_stored` true**: the rebuilt OpenBao opens what the old one
  sealed. This is the drill's point.
- `pve2-env` exits 0 again.
- The audit log shows each caller from its listed address.

## Finish

Delete `/srv/openbao/data.before-drill`. **It is a full copy of every secret**, openable with the seal
key, so it does not outlive the drill.

**To undo before that**, stop OpenBao, move the old storage back, start it, and revert the vault
commits from steps 3 and 4. The old OpenBao's keys are the vault's, so nothing it holds differs from
the rebuilt one but the AppRoles.
