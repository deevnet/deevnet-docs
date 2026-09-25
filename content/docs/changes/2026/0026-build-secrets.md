---
title: "CHG-0026: Build Secrets Off the Disk"
weight: 26
---

# CHG-0026: Build Secrets Off the Disk

| | |
|---|---|
| **Date** | 2026-09-25 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-09-25.** Builds fetch the Proxmox token per run from OpenBao as the read-only image-factory AppRole, and nothing on the Builder holds a build secret on disk. The AppRole's credentials are vaulted and pushed (inventory #56); the hand-off file is deleted. |
| **Window** | 2026-09-25 05:15 to 05:30 EDT |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao: one mount, one policy, one AppRole, two KV entries). The Builder (`dv00bld001p01`): three plaintext env files deleted |
| **Automation** | `deevnet.mgmt` `site.yml --tags openbao`; `deevnet-image-factory` `scripts/pve-creds` and Makefile; `deevnet-tenant-fabric` Makefile. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Additive in OpenBao; the builds keep an inventory fallback (`PVE_CREDS_SOURCE=inventory`) |
| **Related changes** | [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/) (OpenBao) |
| **Related incidents** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/): why a generated credential is pushed before its source is deleted |
| **Related runbooks** | [Build-Time Secrets](/docs/runbook/substrate/building-recovery/build-secrets/) |

---

## Summary

The image factory's Packer builds and the tenant fabric's Terraform need a hypervisor's Proxmox API
token. `pve-env.yml` rendered it into `build/pve-env/<node>.env` on the Builder, and the Makefiles
sourced that file. The files were owner-only, but they outlived every build. Three were there:
`pve.env` and `pve2.env` from 3 September under the old node names, and `dv02hyp002p02.env`.

Worse, the fabric's Makefile only re-rendered its file when it was missing. It had been reading the
3 September `pve2.env` ever since. That is the silent stale node name the rename runbook warns
about.

The operator asked for the secret to come from the site's secrets manager instead.

## Goal

- No build secret is written to disk. `find` finds no `*.env` holding one, and none is created by a
  build.
- Builds read the Proxmox token from OpenBao as a read-only identity, with a short token that is
  revoked after one read. Reading the inventory vault directly stays as the fallback.
- The fabric plan still shows no changes, and `packer validate` passes.

## What was done

1. **No files (image factory, tenant fabric).**
   - `scripts/pve-creds` prints `TF_VAR_proxmox_*` exports on stdout, and the recipes `eval` them.
     It uses Ansible's libraries in-process, so `{{ vault_* }}` references resolve and nothing is
     logged.
   - `pve-env.yml` and every rendered file are deleted.
   - The fabric fetches per run for `PVE_HOST`, whose default is now `dv02hyp002p02` rather than the
     slot name `pve2`.
2. **OpenBao** (the `openbao` role; its play is now tagged `openbao`):
   - KV v2 mount `image-factory`;
   - policy `image-factory`, read-only on `image-factory/data/proxmox/*`;
   - AppRole `image-factory`: 15-minute, 1-hour-maximum, 3-use tokens;
   - the `ansible` policy may now write that mount;
   - the role writes `proxmox/<node>` from each hypervisor's inventory values, and only when they
     differ;
   - it issues the AppRole's credentials once, into a 0600 hand-off file.
3. **Default:** `pve-creds` reads OpenBao. `PVE_CREDS_SOURCE=inventory` reads the vault directly.

## Verification

| Check | Result |
|---|---|
| Inventory source, both nodes: Proxmox `/version` | 200, 200 |
| OpenBao source vs inventory source, both nodes (hashed, never printed) | identical |
| Proxmox `/version` with the OpenBao-sourced token | 200 |
| AppRole token: read `image-factory/data/proxmox/dv02hyp002p02` | 200 |
| … read `deevnet-api/data/backends` / list `sys/mounts` / write `image-factory/…` | 403 / 403 / 403 |
| … after its three uses, or after `revoke-self` | 403 |
| `--tags openbao` second run | `changed=0` |
| `packer validate` (Fedora 44) with credentials from OpenBao | valid |
| `make fabric-plan` with credentials from OpenBao | no changes |
| `find deevnet-image-factory -name '*.env'` | nothing |

No template was built and nothing was applied: validate and plan prove the credentials, and a
template build would change the hypervisor.

## Undo

- Set `PVE_CREDS_SOURCE=inventory` for the builds.
- In OpenBao, delete the `image-factory` AppRole, policy and mount.
- Nothing needs restoring on the Builder: no file was ever the source of truth.

## Follow-ups

- [x] The operator vaulted `vault_openbao_image_factory_role_id` / `_secret_id`
      (`group_vars/all/vault.yml`); committed and **pushed**, with ciphertext checked on origin
      (inventory #56); then `.openbao/image-factory-approle.json` was deleted
- [ ] Later: narrow the Proxmox token itself. `terraform-prov@pve` has `Administrator` at `/`
      ([Build a Management Plane](/docs/runbook/substrate/building-recovery/build-management-plane/),
      Step 7)
