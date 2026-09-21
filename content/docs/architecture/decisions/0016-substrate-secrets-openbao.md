---
title: "ADR-0016: Substrate Secrets in OpenBao"
weight: 16
---

# ADR-0016: The Substrate Keeps Its Runtime Secrets in OpenBao

|  |  |
|--|--|
| **Status** | Accepted |
| **Accepted** | 2026-09-19, recording what [CHG-0010](/docs/changes/2026/0010-tenant-api-cutover/) built on 2026-09-17. The record's own Current state already read *"Proposed, and deployed"*; the status field had simply not caught up. |
| **Date** | 2026-09-17 |
| **Scope** | Where the credentials substrate services use at runtime are kept, how tenant secrets are protected at rest and in transit, and where the internal certificate authority lives |
| **Extends** | [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/0015-tenant-onboarding-through-api/), whose API holds credentials for PowerDNS, the core router, the state store and the tenant hypervisor, and stores tenant secrets |
| **Extended by** | [ADR-0021: Tenant Secrets](/docs/architecture/decisions/0021-tenant-secrets/) (Proposed), the record §8 asked for on tenant namespaces |
| **Related** | [ADR-0012: IoT Platform Services Through a Deevnet API and Terraform Provider](/docs/architecture/decisions/0012-iot-platform-api/) §9 (credential delivery), [ADR-0013: Management-Hypervisor Services Run as Containers on Domain VMs](/docs/architecture/decisions/0013-management-services-domain-vms/), [ADR-0014: Tenant State Durability](/docs/architecture/decisions/0014-tenant-state-durability/) |

---

## Context

### How the API's credentials are handled in ADR-0015's first slice

| Credential | Kept in | Reaches the API as | Can do |
|---|---|---|---|
| Operator token, database password | inventory vault | a root-only env file, then container environment | the whole API; its database |
| PowerDNS HTTP API key | inventory vault; also in `pdns.conf` on the DNS host | the same env file | every zone and key on the server |
| Core router API key | the router automation user's vault entry | the same env file | everything that user may do on the router |
| State-store admin | inventory vault | the same env file | user and policy administration |
| Proxmox token | inventory vault | the same env file | what ADR-0015 grants it on the tenant hypervisor |

And for what is handed to tenants:
- **At rest:** the TSIG and state-store secrets are stored in the clear in the API's database.
- **In transit:** they travel in the create response over plain HTTP, and the state store is plain
  HTTP too.

### What is wrong with that

1. **Nothing on the tenant path is encrypted in transit.** The API, the state store and PowerDNS's
   API all speak plain HTTP. The internal certificate authority is an unstarted roadmap item
   ([SSL Cert Automation](/docs/roadmap/infrastructure/ssl-cert-automation/)).
2. **Tenant secrets are stored in the clear** in a database on the provisioning VM's OS disk.
3. **Every runtime credential is a long-lived value copied into env files.** Rotating one means an
   inventory commit and a re-run of each role that copies it. Root on the VM can read them all with
   `podman inspect`.
4. **There is no single-use credential to hand a tenant.** ADR-0015 needs one so that tenant Terraform
   never holds the operator token.

Each has a local fix: a self-signed certificate, an AES key in the vault, an enrollment table in the
API. Each fix is its own mechanism to build, rotate and audit. Together they amount to a secrets
manager.

---

## Options considered

### A — Keep ansible-vault, fix each weakness locally

- **Pros:** no new service.
- **Cons:** four mechanisms of our own. Credentials stay long-lived copies. The certificate authority
  is still missing.
- **Verdict:** Rejected.

### B — HashiCorp Vault Community Edition

- **Pros:**
  - The same vendor and license (BSL 1.1) as the Terraform the site already runs.
  - The reference implementation, with the widest documentation and tooling.
- **Cons:**
  - **No unattended unseal without a cloud KMS.** HashiCorp's seal documentation lists the cloud KMS
    seals, PKCS#11 (Enterprise) and Transit, which needs another Vault
    ([Vault seal types](https://developer.hashicorp.com/vault/docs/configuration/seal)). Unattended
    recovery on a site with no internet would be a script feeding unseal key shares at start.
  - **Namespaces are Enterprise only** ([Vault editions](https://developer.hashicorp.com/vault/tutorials/get-started/available-editions)),
    which closes off per-tenant isolation later.
- **Verdict:** Rejected, on unseal and namespaces, not on license: the site already accepts BSL for
  Terraform.

### C — OpenBao

The Linux Foundation fork of Vault, MPL 2.0.

- **Pros:**
  - **A native static-key seal:** *"The static key seal configures OpenBao to use static keys provided
    alongside the configuration file as the Auto Unseal mechanism"*
    ([OpenBao static seal](https://openbao.org/docs/configuration/seal/static/)).
  - **Namespaces in the free version**, with per-namespace sealing since 2.6.0 (2026-07-14,
    [release notes](https://openbao.org/community/release-notes/2-6-0/)).
  - **The same API as Vault**, so Vault clients and the `hashicorp/vault` Terraform provider work
    against it.
- **Cons:**
  - A fork, with a smaller community.
  - No Terraform provider of its own. Newer OpenBao-only options can't be set through the Vault
    provider.
  - The docs caution that the static seal is *"only recommended when an existing source of trust …
    already exists"*.
- **Verdict: Chosen.** The existing source of trust is ansible-vault (§2).

### D — step-ca for certificates, plus local fixes for the rest

- **Cons:** a certificate authority, but still A for everything else.
- **Verdict:** Rejected.

**The Terraform connection, weighed.** Substrate services are configured by Ansible, not Terraform,
so neither product would be driven through a Terraform provider on the substrate side. Tenants don't
talk to the secrets manager in the scope decided here (§8).

---

## Decision

**Option C: OpenBao, for substrate runtime secrets, now.**

### 1. One instance, in the identity VM

- **Placement:** OpenBao runs as a container in `dv02idn001v01`, the identity domain VM on Platform
  ([ADR-0013](/docs/architecture/decisions/0013-management-services-domain-vms/)), beside tenant DNS.
- **Why Platform:** the Deevnet API reaches it directly. Tenants can later redeem single-use tokens
  there (§4).
- **Reachable from tenant transit.** The control is its authentication and policies, not the network.
- **Storage:** integrated Raft, single node, on a data disk. Its data is kept data under ADR-0014: a
  scheduled snapshot, copied off the VM.

### 2. It unseals itself from a key ansible-vault delivers

- **The static seal key** is a 32-byte file written root-only by the role from ansible-vault. OpenBao
  unseals on every start with no operator.
- **ansible-vault stays the root of trust** for what OpenBao can't hold about itself: the seal key,
  the recovery key shares and the initial root token.
- **Its password is held by a person, not by a file on the control node.** That is deliberate, and it
  is the one link in the chain that automation cannot follow. The vault password unlocks the seal key,
  the seal key unlocks OpenBao, and OpenBao holds every runtime credential on the site — so a password
  file on the Builder would make shell access to the Builder equivalent to holding every secret here,
  including for anything running there on an operator's behalf. The cost is that a change needing
  vaulted values cannot run unattended, and that cost is accepted: see
  [Vault Operations](/docs/runbook/building-recovery/vault-operations/) for the practice that makes a
  short decrypted window safe.
- **The root token is not kept in use.** After bootstrap, Ansible works through its own AppRole, and
  the root token is revoked. A new root is generated with the recovery keys when needed.

### 3. What goes in now

| Engine | Path | Used for |
|---|---|---|
| KV v2 | `deevnet-api/` | the API's backend credentials: PowerDNS key, router key, state-store admin, Proxmox token. The API's env file carries only its AppRole credentials. |
| Transit | `transit/keys/tenant-secrets` | envelope encryption of the TSIG and state-store secrets in the API's database. The key never leaves OpenBao and rotates in place. |
| PKI | `pki/` | the site's internal certificate authority, issuing TLS certificates to the API, the state store and PowerDNS's API. It takes over the role the SSL Cert Automation roadmap planned for step-ca. |
| Response wrapping | `sys/wrapping` | the single-use enrollment token that lets a tenant create itself (ADR-0015 §10) |
| AppRole auth | `auth/approle/` | the Deevnet API, and Ansible after bootstrap, each with a policy naming exactly its paths |

### 4. How the enrollment token works

1. **The operator admits a tenant name** through the Deevnet API.
2. **The API wraps an enrollment record** for that name in a single-use token with a TTL.
3. **The token reaches the tenant repository age-encrypted**, as ADR-0012 §9 decided for tenant
   credentials.
4. **The tenant's first `create` presents it.** The API unwraps it, which spends it, and returns the
   tenant's own token with everything else.

A stolen token is useless once spent, and a spent token that is presented again is visible.

### 5. Ansible configures it over its HTTP API

- **The role** enables engines, writes policies and roles, issues certificates and writes KV entries
  with `ansible.builtin.uri`.
- **Why not `community.hashi_vault`:** its modules need the `hvac` Python library, which isn't on the
  Builder. The HTTP API needs nothing new, and matches how the collections already drive OPNsense.

### 6. Rebuild order

OpenBao comes up before anything that reads from it:
1. OpenBao
2. PowerDNS, the state store and the core router's resolver work, which need certificates and keys
3. the Deevnet API
4. tenants re-apply

A rebuild that loses OpenBao's data is restored from its snapshot. Without one, the PKI root, the
Transit key and the KV entries are re-created. A new Transit key can't decrypt the API's stored
secrets, so the API then re-ensures from tenant state (ADR-0015 §5).

### 7. Clients

- **The Deevnet API** uses OpenBao's own Go client, `github.com/openbao/openbao/api/v2`.
- **Terraform:** where the site ever drives OpenBao from Terraform, the `hashicorp/vault` provider
  works against its API. Nothing in this decision needs it.

### 8. Not now

- **Tenant namespaces:** tenants reading their own secrets from OpenBao instead of from Terraform
  state. That would revisit ADR-0012 §4 and needs its own record.
- **Dynamic database credentials** for the API's PostgreSQL.
- **Short-lived credentials for PowerDNS, the router and the state store.** None has an OpenBao
  secrets engine, so these stay static values, kept in one place and rotated there.

---

## Consequences

**Tenant secrets are encrypted in transit and at rest.** The API serves TLS from the site CA, and the
secrets in its database are Transit ciphertext.

**The API's env file holds one credential instead of five**, and rotating a backend credential is a
KV write, not an inventory commit.

**The site has a certificate authority.** Tenants and the provider trust its CA certificate, which is
delivered with their credentials. The Builder's clients trust it too.

**A new critical service.**
- **While OpenBao is down,** the API can't start, encrypt or decrypt, so provisioning stops. Nothing
  at runtime depends on it: devices, workloads and resolution continue.
- **Its data is kept data** (ADR-0014).

**ansible-vault shrinks to a bootstrap store** (the seal key, recovery shares, and one-time values)
rather than disappearing.

**The static seal key unseals everything.** Anyone with the seal key and a copy of the Raft data
reads every secret. The key gets the same care as the vault password.

---

## Open questions

1. **Root or intermediate CA.** Should `pki/` be the root, or an intermediate under a root kept
   offline, for example in ansible-vault?
2. **Audit device.** A file audit log inside the VM, or shipped to substrate observability
   (`dv02sob001v01`)?
3. **Router key scope.** Carried from ADR-0015: now that the key lives in KV, can it also be narrowed
   to the resolver's endpoints?

## To confirm when building

- **Checked on 2026-09-17 against `quay.io/openbao/openbao:2.6.2`, in a container on the Builder:**
  - A raw 32-byte key file is accepted by the static seal. The server reported `"type":"static"`, was
    initialised with one recovery share, and **came back unsealed after a restart** with no operator.
  - KV v2 read and write, Transit encrypt and decrypt (ciphertext `vault:v1:…`), PKI root generation
    and certificate issue for `api.mobile.deevnet.net` with an IP SAN.
  - An AppRole with a policy naming only its KV path, the Transit key and one PKI role read its KV
    entry and was refused `sys/policies/acl` with `403`.
  - A response-wrapped value unwrapped once. A second unwrap was refused (`400`).
  - The Go client `github.com/openbao/openbao/api/v2` v2.7.0 logged in with that AppRole, read KV and
    round-tripped Transit.
  - `ansible.builtin.uri` read KV. `community.hashi_vault` 6.2.1 failed for want of `hvac` (§5).
- **Confirmed on 2026-09-17 on `dv02idn001v01`, deployed by CHG-0010:**
  - The image runs under the root podman `podman_service` uses, with the role's uid-matched
    directories. It reported `"type":"static","initialized":true,"sealed":false` and **came back
    unsealed after a restart of the container**, with no operator.
  - Re-running the play is `changed=0`, and it authenticates as Ansible's AppRole rather than root.
  - The API reads its backend credentials from KV at start, serves TLS from the site CA, and both
    tenants' Terraform and the provider trust that CA from the delivered file, with no system trust
    store change.
- **Confirmed on 2026-09-17 by the key-change drill**
  ([OpenBao Drills](/docs/runbook/recovery/substrate-secrets-drills/)), on the live site:
  - **A rotated PKI root is picked up.** The `deevnet_api` role compares the CA the host holds with
    `pki/cert/ca`, reissues, and restarts before its own readiness check; `openbao` refetches the CA to
    the control node. Expiry alone does not catch a rotation, because the new root carries the same
    common name.
  - **A Transit key the stored secrets predate does not lock tenants out.** With
    `min_decryption_version` raised past them, the API reads them as empty and logs the reason, tenants
    still authenticate, and a resupply from tenant state reseals under the new version.
- **Still to confirm:**
  - A Raft snapshot restored onto a fresh VM gives back KV, Transit and PKI, and the API decrypts its
    stored secrets. This is now the last unconfirmed claim here, and it is a different exercise from the
    drill above: a restore returns the same issuer and the same key, so it proves durability rather than
    survivability of a key change.

---

## Current state

- **Accepted, and deployed.** CHG-0010 built all of it on 2026-09-17: the instance on
  `dv02idn001v01`, the static seal from ansible-vault, KV, Transit, PKI and response wrapping, and
  AppRoles for the API and for Ansible. The root token is revoked.
- The API holds one AppRole instead of five backend credentials, its TLS certificate comes from the
  site CA, and both live tenants were admitted with response-wrapped enrollment tokens.
- What §8 left out is still out: no tenant namespaces, no dynamic database credentials.
