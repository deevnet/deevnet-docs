---
title: "Build-Time Secrets"
weight: 3
---

# Build-Time Secrets

Two builds need a live Proxmox API token:

| Build | Where | Needs |
|---|---|---|
| Fedora VM templates (Packer) | `deevnet-image-factory`: `make proxmox-fedora-pve1` / `-pve2` | the node's API token |
| The tenant fabric (Terraform) | `deevnet-tenant-fabric`: `make fabric-init` / `fabric-plan` / `fabric-apply` | the tenant hypervisor's API token |

**The rule: a build secret is fetched per run into the build's own process environment. It is
never written to a file and never passed on a command line**
([Security Controls](/docs/policies/risk-management/security-controls/#credentials),
[CHG-0026](/docs/changes/2026/0026-build-secrets/)). Until CHG-0026, the image factory rendered the
token into `build/pve-env/<node>.env`. Those files outlived every build, and one of them, under a
node's old name, was still being read by the fabric weeks later.

---

## How it flows

```
inventory vault (authoritative)          host_vars/<hypervisor>/vault.yml: vault_proxmox_token_*
        │  deevnet.mgmt site.yml --tags openbao
        ▼
OpenBao  image-factory/proxmox/<node>    {url, node, token_id, token_secret}
        │  scripts/pve-creds  (image-factory AppRole: read-only, 15-minute, 3-use token;
        │                      logs in, reads once, revokes its own token)
        ▼
eval "$(…)" in the make recipe           TF_VAR_proxmox_* in that shell only → packer / terraform
```

- `scripts/pve-creds` lives in `deevnet-image-factory`, and both repositories' Makefiles call it.
  It prints `export` lines on stdout and nothing else, and writes nothing.
- It uses Ansible's own libraries in-process to read the inventory: for the AppRole's credentials,
  or with `--source inventory`, for the token itself. It needs the vault password:
  `ANSIBLE_VAULT_PASSWORD_FILE`, or a prompt.
- **Every read is in OpenBao's audit log**, under the image-factory identity. That identity can
  read `image-factory/proxmox/*` and nothing else: not the API's backends, not a mount, not PKI.

## Everyday use

```bash
# Build a template (fetches the credentials itself)
make -C deevnet-image-factory proxmox-fedora-pve2

# Plan the fabric
make -C deevnet-tenant-fabric fabric-plan

# Put the credentials in your own shell, for a hand-run packer or terraform
eval "$(make -s -C deevnet-image-factory pve2-env)"
```

**OpenBao down?** Read the vault directly. It's the same exports, just without the audit trail:

```bash
PVE_CREDS_SOURCE=inventory make -C deevnet-image-factory proxmox-fedora-pve2
```

## Rotating a Proxmox token

1. On the node: `pveum user token add terraform-prov@pve <new-name> --privsep 0`. Note the secret;
   Proxmox shows it once.
2. Put it in `host_vars/<node>/vault.yml` (`vault_proxmox_token_id`, `vault_proxmox_token_secret`).
   Then `make vault`, **commit and push** (see
   [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/#secrets-a-change-produces)).
3. `ansible-playbook playbooks/site.yml --tags openbao` in `ansible-collection-deevnet.mgmt`. It
   writes only a token that differs.
4. Check it, without printing the token:
   ```bash
   eval "$(make -s -C deevnet-image-factory pve2-env)"
   curl -sk -o /dev/null -w '%{http_code}\n' \
     -H "Authorization: PVEAPIToken=$TF_VAR_proxmox_token_id=$TF_VAR_proxmox_token_secret" \
     "$TF_VAR_proxmox_url/version"                       # 200
   ```
5. Then delete the old token on the node: `pveum user token remove terraform-prov@pve <old-name>`.

The Deevnet API has its **own** Proxmox token (`vault_deevnet_api_proxmox_token_*`, in OpenBao's
`deevnet-api/backends`). Rotating the build token doesn't touch it.

## Rotating the image-factory AppRole's secret-id

1. Delete `vault_openbao_image_factory_role_id` and `vault_openbao_image_factory_secret_id` from
   `group_vars/all/vault.yml`, then run `--tags openbao`. With them missing, the role issues a
   new secret-id into `.openbao/image-factory-approle.json` (mode 0600) on the control node.
2. Move both values into `group_vars/all/vault.yml`, then `make vault`, **commit and push**, and
   only then delete the JSON file.
3. To retire the old secret-id, destroy its accessor:
   `auth/approle/role/image-factory/secret-id-accessor/destroy`.

## When it fails

| Symptom | Means |
|---|---|
| `vault_openbao_image_factory_role_id / _secret_id are not in the inventory` | The AppRole's credentials aren't vaulted yet, or the vault isn't readable. Use `PVE_CREDS_SOURCE=inventory` meanwhile |
| `OpenBao POST auth/approle/login: 400` | Wrong or destroyed secret-id. Rotate it as above |
| `OpenBao GET image-factory/data/proxmox/<node>: 404` | No token written for that node. Check the hypervisor is in the `hypervisors` group with `proxmox_token_*`, then run `--tags openbao` |
| `…: 403` | The policy doesn't cover the path |
| The fabric plan shows changes to a node you didn't touch | Check `TF_VAR_proxmox_node`. It now comes from `PVE_HOST` each run (default `dv02hyp002p02`), never from a leftover file |
