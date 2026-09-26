---
title: "CHG-0010: Deploy the Deevnet API and Cut Tenants Over"
weight: 10
---

# CHG-0010: Deploy the Deevnet API and Cut Tenants Over

| | |
|---|---|
| **Date** | 2026-09-17 |
| **Change type** | Build-out and migration — OpenBao and the tenant API are deployed, and tenants stop being built from inventory |
| **Classification** | Disruptive in one step only: the tenant DNS server restarts when its HTTP API is turned on. Everything else adds services or changes objects nothing depends on yet. |
| **Status** | **Complete.** All eleven steps are done. OpenBao, the PowerDNS API, the API and the egress agent are deployed; **tdemo and eds are both live and built entirely through the API**; and the inventory tenant registry and the role tasks that read it are gone. One working-tree edit awaits `make vault`: the two now-unread tenant secret dicts. |
| **Window** | No operator on site needed: every step is a control-node run or an API call. The one restart affects tenant name resolution for seconds, and no tenant is live. |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao, tenant DNS), `dv02prv001v01` (the API, its database, the state store), `dv02hyp002p02` (the tenant hypervisor and exit node), `dv02cor002p01` (the resolver's delegations) |
| **Automation** | `deevnet.mgmt` `openbao`, `powerdns`, `minio`, `deevnet_api`; `deevnet.net` `tenant_egress_agent`; `deevnet-provisioning-api` **v0.2.4** (v0.2.0 as planned, then four defects the run and the rebuild found); `terraform-provider-deevnet` v0.1.0; the tenant repositories `deevnet-tenant-tdemo` and `eds` |
| **Risk** | Medium. OpenBao becomes a service everything else needs to start, and its seal key is the root of the whole arrangement. The API gains write access to tenant DNS, the resolver, the state store and the tenant hypervisor. |
| **Related decisions** | [ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/) — what the API builds and what a tenant holds; [ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/) — where the credentials live; [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §5 and §9; [ADR-0014](/docs/architecture/decisions/0014-tenant-state-durability/) |
| **Related changes** | [CHG-0008](/docs/changes/2026/0008-domain-vms-build-out/) — built the VMs this deploys into, and created eds's zones, key and state credential; [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) — the zone policy this adds two rules to, still unapplied |
| **Related runbooks** | Provisioning a Tenant (the inventory-driven procedure, removed from the docs 2026-09-23; in git history as `runbook/tenant/legacy-provisioning.md`) — replaced by this change's step 9 and, today, [Tenant Admission](/docs/runbook/substrate/tenant-admission/) |

---

## Summary

ADR-0015 moves everything about a tenant behind the Deevnet API, and ADR-0016 puts the credentials
that needs into OpenBao. This change deploys both and cuts the two tenants over.

**After it:**
- A tenant is admitted with a single-use enrollment token, then declares itself, its workloads and
  its names through one provider. It holds no Proxmox credential, no vault access and no index.
- The API holds the privileged credentials, reading them from OpenBao at start.
- Tenant secrets are Transit-encrypted in the API's database and travel over TLS from the site CA.
- The exit node renders tenant VRF routes from the API instead of from `deevnet_tenants`.

**What it does not do:** apply the zone policy (CHG-0007), retire `deevnet_tenants` from the roles
that still loop over it, or build the broker. Those are follow-ups.

## Before starting

**Secrets.** All but one are already generated and placed, in the working tree's decrypted vault
files; they only need `make vault` and a commit. Regenerate any of them with the command shown if
you would rather not use a value an agent produced.

**`vault_openbao_seal_key`** and `vault_openbao_seal_key_id` — `group_vars/openbao/vault.yml`, a new
file. The static seal key: 32 bytes, base64. OpenBao unseals itself with it on every start, so
whoever holds it and a copy of the Raft data reads every secret. It gets the same care as the vault
password.

```bash
head -c 32 /dev/urandom | base64
```

**`vault_powerdns_api_key`** — `group_vars/all/vault.yml`. Global to the DNS server, so it goes only
to the API. Setting it is what turns the HTTP API on.

```bash
openssl rand -hex 32
```

**`vault_minio_deevnet_api_secret`** — `group_vars/all/vault.yml`. The API's own state-store admin
user, never root.

```bash
openssl rand -hex 20
```

**`vault_deevnet_egress_agent_token`** — `group_vars/all/vault.yml`, because two hosts need it: the
API serves it as `DEEVNET_AGENT_TOKEN`, and the tenant hypervisor presents it. It reads the VRF list
and nothing else.

```bash
openssl rand -hex 32
```

**`vault_deevnet_api_token_hmac_key`** — `group_vars/deevnet_api/vault.yml`. The MAC key of tenant
tokens. A tenant can restore itself after the registry is lost only while this key is unchanged, so
it outlives the database and is not regenerated casually.

```bash
head -c 32 /dev/urandom | base64
```

**`vault_deevnet_api_proxmox_token_id` and `_secret`** — `group_vars/deevnet_api/vault.yml`. Issued
on hv02: role `DeevnetTenantBuilder`, token `deevnet-api@pve!tenants`, with `Sys.Audit` scoped to
`/nodes` through `DeevnetNodeAudit`. Proxmox shows a secret once, so re-issuing means deleting and
re-creating the token.

**`vault_openbao_ansible_role_id` and `_secret_id`** — `group_vars/openbao/vault.yml`, commented out
there for now. **These are the one exception: step 3 produces them**, in
`.openbao/dv02idn001v01-init.json` on the control node, with the recovery key. Move all three into
the vault and delete the file.

**Encrypt before committing:**

```bash
cd ansible-inventory-deevnet && make vault
```

The pre-commit hook refuses a plaintext `vault.yml`, and `make vault` finds every one of them,
including the new `group_vars/openbao/` file.

**Images staged on the Builder:**

```bash
# OpenBao
cd ansible-collection-deevnet.builder && make artifacts     # or the artifacts play
# The API, tagged and staged
cd deevnet-provisioning-api && make test && git tag v0.2.0 && make stage
```

Then set `deevnet_api_version: "v0.2.0"` in the `deevnet_api` role or inventory.

## Procedure

Each step states what it changes, how it is checked, and how it goes back.

### 1. Stage the images

`artifacts` on the Builder for OpenBao, `make stage` for the API.

**Verify:** `/srv/deevnet-http/container-images/openbao/openbao-2.6.2.tar` and
`deevnet-api/deevnet-api-v0.2.0.tar` exist.
**Back:** nothing was changed.

### 2. Add the OpenBao host

Put `dv02idn001v01` in the `openbao` group in `mobile/hosts.yml`. The group is deliberately empty
until now, so a missing seal key cannot stop a `site.yml` run.

### 3. Deploy OpenBao

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02idn001v01
```

The first run initializes it, enables KV, Transit, PKI and AppRole, generates the site CA, hands
Ansible its own AppRole and **revokes the root token**.

**Verify:**
- `.openbao/dv02idn001v01-init.json` on the control node holds the recovery key and Ansible's
  AppRole. Move all three into the vault, then **`make vault`, commit and push** — and only then
  delete the file. These values exist nowhere else, and losing them means rebuilding OpenBao
  ([INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/)).
- `.openbao/site-ca.pem` exists.
- Re-run the play: `changed=0`.
- Restart the VM, or the container, and confirm OpenBao comes back **unsealed**.

**Back:** stop and disable the container. Nothing reads from it yet.

### 4. Turn on PowerDNS's HTTP API

With `vault_powerdns_api_key` in place, re-run the `powerdns` play on `dv02idn001v01`.

**This restarts `pdns-auth`.** Tenant names stop resolving for a few seconds. No tenant is live.

**Verify:** `curl -H "X-API-Key: …" http://10.20.25.21:8081/api/v1/servers/localhost/zones` answers
from the provisioning VM and **is refused from anywhere else** (the webserver admits only that
address). The eds zones still resolve through the core router.
**Back:** remove the vault key and re-run; the API turns off and the server restarts again.

### 5. Create the API's state-store user

Re-run the `minio` play on `dv02prv001v01`.

**Verify:** `mc admin user info local deevnet-api` shows the `deevnet-api-admin` policy. The `tf-state`
bucket and eds's own user are untouched.
**Back:** `mc admin user remove local deevnet-api`.

### 6. Deploy the API

Set `deevnet_api_site: "{{ deevnet_substrate }}"` and run the `deevnet_api` play. It writes the
backend credentials into OpenBao KV, issues the API's TLS certificate from the site CA, gives the
container its AppRole, and restarts it.

**Verify, from the Builder:**
- `curl --cacert .openbao/site-ca.pem https://api.mobile.deevnet.net:8080/readyz` → `200`, and
  plain HTTP is refused.
- `/version` reports `v0.2.0`.
- `GET /v1/tenants` with the operator token → `{"tenants":[]}`.
- The container's env file holds **no backend credential**: no PowerDNS key, no router key, no
  state-store secret, no Proxmox token, no token MAC key. Those five are in OpenBao KV. It does hold
  four credentials that are not backends' — the AppRole that fetches the rest, the database URL, the
  operator token and the egress agent's token.

**Back:** unset `deevnet_api_site` and re-run: the API goes back to answering 501 on `/v1`.

### 7. The two narrow zone rules

Declare, in `firewall.yml`: `platform -> management` from the provisioning VM to the tenant
hypervisor's API port, and the provisioning VM to the core router's API on Platform.

The router passes everything until CHG-0007 applies the policy, so this step is a declaration now
and an enforcement later. Recording it here is what keeps CHG-0007 from breaking the API.

### 8. The egress agent

Add `vault_deevnet_egress_agent_token`, set the same value as the API's `DEEVNET_AGENT_TOKEN`, then:

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/tenant-egress-agent.yml
```

**Verify:** the timer is enabled, one run has happened, and `/etc/frr/frr.conf.local` matches the
API's list (empty until step 9). Then set `proxmox_tenant_egress.agent_managed: true`.
**Back:** stop and disable the timer, set `agent_managed: false`, and re-run
`proxmox-node-network.yml`, which writes the file from inventory again.

### 9. Cut tdemo over — the drill

tdemo is the reference tenant, and applying it is the rebuild drill (ADR-0015 §9).

```bash
# Operator, on the Builder
curl --cacert site-ca.pem -H "Authorization: Bearer $OPERATOR" \
  -X POST https://api.mobile.deevnet.net:8080/v1/admissions -d '{"name":"tdemo"}'
```

Then in `deevnet-tenant-tdemo`, with the enrollment token as `DEEVNET_API_TOKEN`: `make init`,
`make apply`.

**Verify:**
- the API's zone, VNet and subnet exist on hv02, and its VM runs with the derived VMID, MAC and
  address
- `dig @10.20.99.1 app.tdemo.mobile.deevnet.net` answers, and the PTR resolves back
- the workload reaches the internet through the perimeter, and **not** the management segment
- `/etc/frr/frr.conf.local` gained `vrf vrf_tdemo` within the timer's interval
- a second `terraform plan` is empty
- `make state-backend`, migrate state, and plan again: still empty

**Then the restore drill:** stop the API, `DROP` its tenant rows, start it, and apply tdemo again. It
must come back on the same index with the same keys, and the plan must end empty.

**Finally** `make destroy`, and confirm hv02 has no tenant zone, VNet or VM left, and the resolver
has no tdemo delegation.

### 10. Cut eds over

Admit `eds`, then apply the tenant in the EdS monorepo.

**What happens to what CHG-0008 created:** the zones and the state-store user are **adopted** — the
API ensures them rather than recreating them. The **TSIG secret is replaced** by the one the API
generates, and eds's Terraform state becomes its authoritative copy. Nothing holds the old secret
except the vault, and eds has never applied, so nothing is disturbed.

**Verify:** as step 9, plus `palette` and `lightd` resolving to the workload.

### 11. Retire what the API replaced

**Done 2026-09-17**, after both tenants were proven and after the key-change drill proved the API can
create and re-create these objects unaided — the order matters, because this step deletes the only
other thing that could create them.

Four roles read the inventory registry, not three: `proxmox_node_network` did too, through
`proxmox_tenant_egress.tenants`, and emptying the registry would have failed its assert on every run.

- **`powerdns`** keeps the server, its schema and its HTTP API; loses zone creation, TSIG import, key
  binding, the update ACL and apex reconciliation.
- **`minio`** keeps the bucket, its versioning and the API's admin user; loses the per-tenant policy
  and user.
- **`opnsense_dns`** loses tenant zone delegation entirely. Checked first that nothing in it prunes
  forward entries, so the API's rows survive a run — `dns_delete_unmanaged` reaches host overrides and
  aliases only.
- **`proxmox_node_network`** stops requiring a tenant list when the agent owns the file, and verifies
  the VRFs the node actually has instead — a better check, because it tests what is there rather than
  what was declared.
- **`deevnet_tenants` is gone**, along with `vault_tenant_tsig_keys` and `vault_tenant_state_keys`,
  whose values were stale as well as unread: the API replaced eds's TSIG secret when it adopted the
  zone.

**`deevnet_tenant_fabric` is NOT unused**, as this record previously claimed. The `deevnet_api` role
reads `controller_id` and `node` from it, which is how the API knows where to attach a tenant's zone.
It stays.

**Verified after the removals:** all four roles run clean, and both tenants' zones still resolve
forward and reverse with the API's SOA, both state users are intact, both VRFs verify for their
default route and for leaving via the perimeter, and both tenants' plans are clean.

Three pull requests, one per repository.

## What the run found

Ten of the eleven steps ran on 2026-09-17. Nine defects surfaced, all of them only findable by
running it: six were in code that had never met the real thing, and three were in claims the
documents made about it.

**The API could not start.** It wanted six workload settings — VMID base, MAC namespace, template
prefix, storage, disk and cloud-init user — that the workload slice (ADR-0015 §12) needs and the
`deevnet_api` role never wired. The values are the ones already in use, and the MAC namespace is the
site fact the `vm_identity` allocator uses, so tenant and substrate VMs cannot mint the same address.
VM 2040 carries `02:de:20:00:07:f8`, and `0x07f8` is 2040.

**Its database could not read its own files.** `PGDATA` was created root-owned on the claim that the
postgres entrypoint hands it over on first init. It does not: it re-execs as postgres *before* it
chowns, and swallows the failure. The server could not open `global/pg_filenode.map`, which presents
as `database: unreachable` rather than as a permission problem.

**Ansible's AppRole was unreachable from the API host.** It is kept with OpenBao's other bootstrap
secrets in `group_vars/openbao`, and the provisioning VM is not in that group. It is now read from
the OpenBao host, the way the router's API key is read from the router.

**The first apply spent its token and then failed.** A tenant's first apply is configured with the
single-use enrollment token; creating the tenant spends it, and the provider kept using it, so the
workload that followed got `401`. The tenant's own token comes back in that create response and now
carries every later call in the run.

**A name beside a workload claimed the workload's reverse record.** Every published record wrote a
PTR with `REPLACE`, so `10.20.129.10` resolved back to `service.tdemo` instead of `app.tdemo`, and
removing the alias would have taken the workload's PTR with it. A workload owns its address and
publishes the PTR; a name a tenant adds beside it is forward only.

**A tenant could not restore itself, twice over.** The registry-loss drill found both halves:

1. **The API answered `401`.** A tenant token verifies by its MAC without the registry — the whole
   point of a token that outlives the database (ADR-0015 §5) — and then the handler admitted only a
   *registered* tenant. An unregistered tenant now gets the same `404` as a tenant asking about a
   name that is not its own.
2. **The provider reported "no changes" while the tenant was gone.** `Read` set `present: false` as
   designed, but every issued attribute keeps its state value in a plan, so nothing differed and the
   restore never ran. This was the worst of the nine: an apply that claims a match while the
   substrate holds nothing.

**The audit log credited the operator with everything**, because the actor was a constant. It was
attributing tdemo's own restore and workloads to the operator, and names a tenant published were not
audited at all.

**Two claims in these documents were wrong.** The API's env file does hold four credentials, not
one — corrected in step 6 above. And the zone policy matrix could not express a rule narrowed to a
host and port at all, which step 7 needed; the role learned to.

## Field notes

**Destroying a tenant revokes the credential its state backend is using.** The teardown drill
completed on the substrate and then Terraform could not write its state back: the state-store user
had just been deleted along with the tenant. The stale lock object had to be removed by hand. A
decommission migrates to local state first, and a tenant that is being rebuilt starts from local
state too.

**tdemo took index 1 and eds took index 2**, which is the reverse of what inventory had recorded.
eds's forward zone was adopted; the reverse zone for index 1 had been bound to eds's TSIG key by
CHG-0008, and the API rebound it to tdemo and purged the stale records, which is what
`purgeIfHandedOver` exists for. **Until step 11 runs, do not run the `powerdns`, `minio` or
`opnsense_dns` plays for tenants**: inventory still says eds is index 1 and the roles would fight the
API over the same objects.

**The Builder's second artifact server fails `--tags container-images`.** `dv02bld001v01` is declared
an artifact server but has never had the role run, so nginx is absent and the image tasks fail
chowning to a user that does not exist. The Builder itself staged both images; this host is a
follow-up, not part of this change.

**hv02 carries the tenant SNAT rule twice.** Identical duplicates, harmless, presumably from repeated
SDN applies. Noted rather than fixed.

## What went wrong afterwards

Step 3's own instruction — move the values into the vault, then delete the init file — was followed
while the inventory was decrypted, and a `git reset --hard` run eight minutes later during the pull
request merges discarded the plaintext. OpenBao's recovery key and Ansible's AppRole were
unrecoverable, and the instance had to be rebuilt.
[INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) has the detail, the routes that were
ruled out, and the three latent defects the rebuild exposed.

**Step 3's verification is amended accordingly:** encrypting, committing and **pushing** the values is
part of that step, and the init file is deleted only afterwards. See
[Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/).

## Rollback, as a whole

Nothing here replaces a working service: OpenBao and the API are new, and the tenants they build did
not exist. The order back is the order forward, reversed — destroy the tenants, stop the agent, unset
`deevnet_api_site`, remove the MinIO user, turn off the PowerDNS API, stop OpenBao — and the
substrate is where CHG-0008 left it.

## Follow-ups

- **ADR-0014:** the API's database now holds tenant secrets and the registry, and OpenBao's storage
  is secrets too. Both sit on VMs with no off-host copy.
- **CHG-0007:** applying the zone policy, with step 7's two rules in it.
- **Step 11**, the one step of this change left: retiring the per-tenant loops from the `powerdns`,
  `minio` and `opnsense_dns` roles, which is what finally empties `deevnet_tenants`. Until then those
  plays and the API disagree about eds's index.
- **The provider mirror** (ADR-0012 §7), so a tenant's `terraform init` works offline instead of
  needing a locally built provider. Until it exists the tenants' lock files cannot be committed,
  because the only source is a locally built binary whose checksum is nobody else's.
- **`dv02bld001v01` as an artifact server**, or removed from the group: `--tags container-images`
  fails there for want of nginx's user.
- **The duplicate tenant SNAT rule** on hv02.
- **A Raft snapshot restored onto a fresh VM**, which ADR-0016 still lists as unconfirmed.
- **age-encrypted credential delivery** (ADR-0012 §9) for the enrollment token.
- **The broker** (ADR-0012 §8), and then the IoT resources.
- **Accept ADR-0010, ADR-0012, ADR-0014, ADR-0015 and ADR-0016** once this has run.
