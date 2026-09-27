---
title: "CHG-0028: Tenants Log In to Their Own Workloads"
weight: -28
---

# CHG-0028: Tenants Log In to Their Own Workloads

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled |
| **Site** | mobile |
| **Systems** | `dv02hyp002p02` (a new `fedora-tenant-44-*` template), `dv02prv001v01` (the API), `dv02cor002p01` (one rule), `dv02obs001v01` (tenant downloads: the new provider), the eds and tdemo workloads (rebuilt) |
| **Automation** | `deevnet-image-factory` `make proxmox-fedora-tenant`; `deevnet-provisioning-api` `make stage`; `terraform-provider-deevnet` `make stage`; `deevnet.mgmt` `site.yml --tags deevnet-api` and `--tags tenant-downloads`; `deevnet.net` `make migration-opnsense-firewall`. Inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium — the API switches to a template prefix that matches nothing if Step 2 has not produced the template, and every workload create then fails |
| **Related changes** | [CHG-0012](/docs/changes/2026/0012-operator-access-to-tenants/) (whose shared-key follow-up this closes), [CHG-0022](/docs/changes/2026/0022-tenant-dev-network/) |
| **Related incidents** | None |
| **Related runbooks** | [Tenant Admission](/docs/runbook/substrate/tenant-admission/), [Network and Workloads](/docs/runbook/tenant/services/network-and-workloads/) |

---

## Summary

Implements [ADR-0028](/docs/architecture/decisions/tenant-model/0028-tenant-workload-login/).

Today a tenant can build a workload and cannot log in to it. The only key on a tenant VM is the
substrate's `a_autoprov` automation key, with passwordless sudo, and the operator installs tenant code
by hand. `ssh_keys` has never worked: the API encoded each space in a key as `+`, which Proxmox kept.
`DVNTM-TD` has no path to the tenant overlay.

After this change a tenant puts its **public** key in `ssh_keys` and logs in from `DVNTM-TD` as the
account the workload reports as `login_user`. Tenant workloads clone a template with no `a_autoprov`,
so the substrate has no standing access to them.

The same API release also stops a deleted tenant's MQTT accounts from staying live in the broker. A
tenant admitted later under the same name would have inherited them.

## Goal

- `fedora-tenant-44-*` exists on `dv02hyp002p02`, and a clone of it has no `a_autoprov` user, home,
  key or sudoers entry.
- The API reports `v0.9.0`, and a workload's response carries `"login_user": "tenant"`.
- From a laptop on `DVNTM-TD`, `ssh tenant@<workload fqdn>` logs in with the key in `ssh_keys`, and
  `sudo -n true` succeeds.
- On that workload, the substrate's automation key is refused, and so is another tenant's key.
- From `DVNTM-TD`, only port 22 on the overlay answers; nothing else in the overlay does.
- Deleting a tenant that holds a broker account removes the account from the broker.
- The eds and tdemo workloads are rebuilt from the tenant template, and nothing of `a_autoprov` is on
  them.
- The downloads site serves provider `0.5.0`, which has `login_user`.

## Scope

**In scope:** the tenant template, the API and provider releases, the role defaults, one firewall
rule, rebuilding the two existing workloads, the tenant guide's login pages.

**Out of scope:**
- Unattended code delivery (ADR-0017).
- An SSH CA (ADR-0025).
- Changing keys on a running workload.
- Per-tenant `DVNTM-TD` keys and client isolation (the next change).
- TLS on the state store.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The API's new prefix matches no template | API, `hyp002` | Step 2 must produce the template before Step 3 deploys the role. The Step 3 verify creates a workload |
| The build's `userdel` fails while Packer is logged in as `a_autoprov` | image factory | `-f`, and the whole removal is one `sudo` as the last command. A failure fails the build, and no template is written |
| cloud-init gives `tenant` no sudo | clone | The Step 4 verify runs `sudo -n true`. Fedora's `default_user` carries passwordless sudo; this is the first time it is relied on |
| Tenants reach each other's workloads on port 22 | router | Zone-level by design (ADR-0028 §5). Only the key protects a workload, and the Step 4 verify proves another tenant's key is refused |
| Rebuilding eds loses what the operator installed on it | eds `services` | eds's owner reinstalls it over the new login. This is the first real use of the path |
| Existing workloads re-adopted with `ciuser=tenant` | Proxmox | Harmless: the config changes but the guest keeps its original account until rebuilt, which Step 6 does |

## Prerequisites

- [ ] PRs merged: `deevnet-provisioning-api` `chg-0028-workload-ssh-keys`, `terraform-provider-deevnet`
      `chg-0028-workload-login`, `deevnet-image-factory` `chg-0028-tenant-template`,
      `ansible-collection-deevnet.mgmt` `chg-0028-tenant-login`, `ansible-inventory-deevnet`
      `chg-0028-tenant-ssh`
- [ ] Vault decrypted, collections built (`make deps install-dev`)
- [ ] A laptop on `DVNTM-TD` with provider 0.5.0 and an ed25519 key
- [ ] INC-0004: `re0` quiet for the window

## Procedure

### Step 1: Build and stage the API and provider

**Run** (on `main` after the merges):

```bash
cd deevnet-provisioning-api && git tag v0.9.0 && git push origin v0.9.0 && make stage
cd ../terraform-provider-deevnet && git tag v0.5.0 && git push origin v0.5.0 && make stage
```

**Verify:** both artifacts are on the Builder.

**Undo:** nothing to undo; nothing running has changed.

### Step 2: Build the tenant template

**Run** (in `deevnet-image-factory`):

```bash
make proxmox-fedora-tenant FEDORA_RELEASE=44
```

**Verify:**

1. The build passes, including its last step, which fails if any trace of `a_autoprov` survives.
2. `qm list` on `dv02hyp002p02` shows `fedora-tenant-44-*` as a template, alongside the
   untouched `fedora-server-44-*`.

**Undo:** `qm destroy <template VMID>`.

### Step 3: Deploy the API

**Run** (in `ansible-collection-deevnet.mgmt`):

```bash
ansible-playbook playbooks/site.yml --tags deevnet-api --limit dv02prv001v01
```

**Verify:**

1. The API reports `v0.9.0` and is ready.
2. Its environment has `DEEVNET_TEMPLATE_PREFIX=fedora-tenant-` and `DEEVNET_TENANT_CIUSER=tenant`.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: Open SSH from `DVNTM-TD`, and prove the login

**Run** (in `ansible-collection-deevnet.net`):

```bash
make migration-opnsense-firewall                                  # plan: 1 to add, nothing else
make migration-opnsense-firewall EXTRA_ARGS="-e firewall_apply=true"
```

Then, from the `DVNTM-TD` laptop, in tdemo, add a throwaway workload `probe` with
`ssh_keys = [file("~/.ssh/id_ed25519.pub")]` and apply.

**Verify:**

1. The plan adds exactly one rule, `tenant dev -> tenant workload SSH (ADR-0028)`.
2. `terraform output` shows `login_user = "tenant"`.
3. `ssh tenant@probe.tdemo.mobile.deevnet.net 'id; sudo -n true && echo sudo-ok'` succeeds.
4. On `probe`: `id a_autoprov` fails; `/home/a_autoprov` and `/etc/sudoers.d/010_a_autoprov-nopasswd`
   are absent.
5. From the Builder: `ssh -o IdentitiesOnly=yes -i <a_autoprov key> a_autoprov@probe…` is refused,
   and so is `tenant@probe…` with the a_autoprov key.
6. Another tenant's key (eds's owner's) is refused on `probe`.
7. From `DVNTM-TD`: `nc -zv probe… 80` times out; `nc -zv 10.20.130.10 22` (eds) connects and is then
   refused for lack of a key.

**Undo:** [Undo Step 4](#undo-step-4)

### Step 5: Prove the broker cleanup

**Run:** as tdemo, create a broker account `probe`, note its username, then destroy `probe` and a
throwaway tenant created for this (admit `tprobe`, apply, create an account, destroy all).

**Verify:** after the tenant delete, the account is gone from the broker's auth database, and a
connection with its password is refused.

**Undo:** nothing; this step only deletes.

### Step 6: Rebuild the existing workloads

**Run:** in tdemo and eds, set `ssh_keys` to the owner's public key, then
`terraform apply -replace=deevnet_workload.<name>`. eds's owner reinstalls its service over the new
login.

**Verify:** on each, step 4's checks 3 and 4 hold. eds's service is back.

**Undo:** none. A rebuilt workload is rebuilt, and the old clone is gone.

### Step 7: Provider on the downloads site, and the tenant guide

**Run:** `ansible-playbook playbooks/site.yml --tags tenant-downloads --limit dv02obs001v01`, then
merge the tenant-guide PR (Network and Workloads, Troubleshooting, the MQTT walkthrough, Coming Soon,
Before You Start, and Tenant Admission §3).

**Verify:** `install-provider.sh` on a scratch home installs `0.5.0`.

**Undo:** revert the PR.

## Verification

The Goal, as a whole, from a `DVNTM-TD` laptop that has never held the automation key.

## Undo

Steps are backed out in reverse order. After Step 6 the old workloads are gone, so undo stops being
practical there. The tenant template and the rule do no harm if left in place.

### Undo Step 3

Set `deevnet_api_template_prefix: "fedora-server-"` and `deevnet_api_tenant_ciuser: a_autoprov` in
inventory, and deploy the `v0.8.1` image with the same tag.

### Undo Step 4

Remove the rule from `firewall.yml` and run the firewall plan and apply again.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] Whether a key change reaches a running workload on reboot (ADR-0028 open question 2).
- [ ] Per-tenant `DVNTM-TD` keys and client isolation.
- [ ] Substrate VMs still clone `fedora-server-*` with the shared key; that is by design, but the key
      has no rotation procedure (credential-rotation roadmap).
