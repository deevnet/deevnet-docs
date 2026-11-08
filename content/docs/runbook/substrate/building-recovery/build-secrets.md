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
        │  scripts/pve-creds  (reads the vault in-process, prints exports, writes nothing)
        ▼
eval "$(…)" in the make recipe           TF_VAR_proxmox_* in that shell only → packer / terraform
```

- **Builds read the vault, never OpenBao.** OpenBao is sealed outside work sessions
  ([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/)),
  and a template build or a fabric plan must not need it open
  ([CHG-0037](/docs/changes/2026/0037-builds-off-openbao/)).
- `scripts/pve-creds` lives in `deevnet-image-factory`, and both repositories' Makefiles call it.
  It prints `export` lines on stdout and nothing else, and writes nothing.
- It uses Ansible's own libraries in-process to read the hypervisor's `host_vars`, so templated
  values resolve as they do in a play. It needs the vault password: `ANSIBLE_VAULT_PASSWORD_FILE`,
  or a prompt.
- **OpenBao still holds a copy that nothing reads**, at `image-factory/proxmox/<node>`, with the
  image-factory AppRole. CHG-0037 step 2 removes both.

## Everyday use

```bash
# Build a template (fetches the credentials itself)
make -C deevnet-image-factory proxmox-fedora-pve2

# Plan the fabric
make -C deevnet-tenant-fabric fabric-plan

# Put the credentials in your own shell, for a hand-run packer or terraform
eval "$(make -s -C deevnet-image-factory pve2-env)"
```

## Rotating a Proxmox token

1. On the node: `pveum user token add terraform-prov@pve <new-name> --privsep 0`. Note the secret;
   Proxmox shows it once.
2. Put it in `host_vars/<node>/vault.yml` (`vault_proxmox_token_id`, `vault_proxmox_token_secret`).
   Then `make vault`, **commit and push** (see
   [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/#secrets-a-change-produces)).
3. Check it, without printing the token:
   ```bash
   eval "$(make -s -C deevnet-image-factory pve2-env)"
   curl -sk -o /dev/null -w '%{http_code}\n' \
     -H "Authorization: PVEAPIToken=$TF_VAR_proxmox_token_id=$TF_VAR_proxmox_token_secret" \
     "$TF_VAR_proxmox_url/version"                       # 200
   ```
4. Then delete the old token on the node: `pveum user token remove terraform-prov@pve <old-name>`.

The Deevnet API has its **own** Proxmox token (`vault_deevnet_api_proxmox_token_*`, in OpenBao's
`deevnet-api/backends`). Rotating the build token doesn't touch it.

## When it fails

| Symptom | Means |
|---|---|
| `<node> has no proxmox_token_id / proxmox_token_secret in the inventory` | The token isn't in `host_vars/<node>/vault.yml`, or the host isn't in the inventory under that name |
| `inventory not found` | `DEEVNET_INVENTORY` doesn't point at the inventory's `mobile` directory |
| The fabric plan shows changes to a node you didn't touch | Check `TF_VAR_proxmox_node`. It now comes from `PVE_HOST` each run (default `dv02hyp002p02`), never from a leftover file |
