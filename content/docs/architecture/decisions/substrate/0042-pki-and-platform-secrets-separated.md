---
title: "ADR-0042: PKI and Platform Secrets Separated"
weight: -42
---

# ADR-0042: The Factory's CA Keys Live in a Secret Store of Their Own, Sealed Except in PKI Sessions

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it) and the [decision register](/docs/architecture/reviews/2026-10-tenant-pki/#decision-register) |
| **Date** | 2026-10-21 |
| **Scope** | Where the mobile site keeps the keys of ADR-0039's Tenants CA, tenant CAs and Names CA; how that store is unsealed, reached, backed up and restored; and how it differs from the secret store the API runs on. Not the CA hierarchy (ADR-0039) |
| **Amends** | [ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) §1 (one OpenBao), §2 (the static seal, which stays for the platform store only) and §3 (the `pki-*` rows); the [Certificates standard](/docs/standards/certificates/) §5, once accepted. Narrows [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)'s rule (keys held in ansible-vault) to the platform store |
| **Related** | [ADR-0039](/docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/) *(Proposed)*, which depends on this; [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/); [ADR-0013](/docs/architecture/decisions/substrate/0013-management-services-domain-vms/); [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/); the [Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/) |

---

## Context

**The mobile site has one OpenBao**, a container on the identity VM (`dv02idn001v01`), beside
PowerDNS. Its static seal key is written to the same VM, so it unseals at every start with no
operator (ADR-0016 §2). Its Raft data is on the VM's OS disk, and **nothing backs it up**: the
backup runbook's row for it says "Nothing yet", and INC-0003's snapshot action is still scheduled.

**What uses it, and when** (read from the code; detail in the
[review](/docs/architecture/reviews/2026-10-tenant-pki/#what-uses-openbao)):

| Consumer | What | When |
|---|---|---|
| The Deevnet API | its backend credentials (`deevnet-api/backends`) | at start: **the API cannot start while OpenBao is sealed** |
| The Deevnet API | Transit (sealing tenant secrets), response wrapping (enrollment tokens), signing tenant service certificates | per request, for provisioning |
| Packer and the tenant fabric | Proxmox tokens (`image-factory/`) | at build time, with an inventory fallback |
| Ansible | configuration | at deploy time |
| Devices, the broker, DNS, the log store, Grafana, tenant workloads | — | **never** |

**So nothing a deployed tenant runs on needs OpenBao.** The broker authenticates from its own
database, and an API outage "stops provisioning, never devices" (ADR-0012). What OpenBao's
availability decides is whether the factory can **provision**.

**ADR-0039 adds keys of a different kind**: an online key that can make CAs, and every
Deevnet-managed tenant's CA keys. Losing them unrecoverably means every managed tenant re-anchors
every device. A copy taken while the store is unsealed is a stolen authority, and with no revocation
it stays valid for years. These keys are needed only when a tenant is created, a certificate is
issued, or a device is enrolled.

## Decision

### 1. Two secret stores, with different seals

| | Platform secret store | PKI secret store |
|---|---|---|
| Holds | the API's backend credentials, Transit, response wrapping, build secrets; the retiring site-level tenant CAs until they are removed | the Tenants CA, every tenant's Service and Device CA, the Names CA |
| Seal | static, from ansible-vault, as today: it starts unattended, so the API does | **Shamir, by the operator**: no unseal material is on the kit |
| Normally | unsealed | **sealed**, except during a PKI session |
| Holds a CA key | no, once the site-level tenant CAs retire (ADR-0039 §11) | yes, only CA keys |

**Calling the first "runtime" would mislead.** No runtime path uses it. It is the platform's
provisioning store, and it keeps the API up unattended.

### 2. The PKI store is a VM of its own

| Option | |
|---|---|
| **A new small VM on the management hypervisor** *(leaning)* | Its own disk, storage, credentials, policies and firewall, on the Platform segment. A normal operation (ADR-0013, the domain-VM pattern), with room on the hypervisor. Its data is sealed at rest, so a hypervisor administrator or a stolen disk gets ciphertext; only a compromise while it is unsealed exposes keys |
| A second container on the identity VM | Least work, but it shares a kernel, root and disk with the platform store and PowerDNS. The seal differs and little else does |
| Dedicated hardware | Physically apart, but one more device to carry, power, back up and keep current, for protection the VM's sealed-at-rest storage mostly gives already |

**Not the offline signer.** The Pi that holds the root and the Site CAs stays offline and keeps its
purpose. The PKI store is online when unsealed, by design.

### 3. A PKI session is deliberate and bounded

**The operator opens a session** by unsealing the PKI store. Then a single command gives the API a
PKI credential that lasts the session (a response-wrapped AppRole secret-ID, a few hours). **The
session ends** when the credential expires or the operator seals the store. Outside a session the
API holds no usable PKI credential at all, so even a compromised API cannot issue.

**The API reports a closed session plainly.** It refuses tenant creation, certificate issuance and
device enrollment before changing anything, and says the PKI is not available. Everything else the
API does is unaffected.

**Unseal material is held off the kit.** Shares, with a threshold of the owner's choosing, are kept
by the operator: one in a password manager, one with the offline signer's media. None is on any
host.

### 4. Backups are encrypted, off the kit, and proven by restoring

**Both stores take Raft snapshots on a schedule and after every PKI session**, copied off the kit. A
PKI snapshot is useless without the unseal shares, which are kept apart from it. **The platform
store's Transit key and backend credentials** are held in ansible-vault by CHG-0036's rule, so that a
rebuild gets the same keys back.

**The PKI store's keys are not copied into ansible-vault.** A CA-making key behind the vault password
alone, on the control node, which travels too, would be a second, weaker custody. The PKI store is
recovered from its snapshot and its shares.

**A backup counts only when a restore has worked.** The test: a snapshot restored onto a fresh VM on
other hardware unseals with the shares. Its issuers keep their identities (the same keys and subject
key identifiers), it issues a certificate that chains as before, and a pinned device accepts it.

### 5. What each failure costs

| Event | Platform store | PKI store |
|---|---|---|
| **Kit stolen while off** | its seal key is on the kit: its secrets are exposed; rotate the API's backend credentials | sealed, shares elsewhere: **no exposure** |
| **Kit stolen while running, no PKI session** | exposed, as above | sealed: no exposure |
| **Kit stolen during a PKI session** | exposed | **treat every key in it as compromised** (below) |
| **Platform store compromised** | rotate its secrets; tenant secrets resealed | untouched: it holds no PKI credential outside a session |
| **PKI store compromised** | — | Tenants CA and tenant CAs compromised: new CAs, reissue, re-anchor; the old ones stay valid until they expire (no revocation) |
| **Hypervisor compromised** | exposed | exposed if unsealed at the time; sealed data is ciphertext |
| **Disk failure, or the whole kit lost** | restore from snapshot and the vault | restore from snapshot and shares, on new hardware; identities unchanged |
| **Interrupted issuance** | — | resumed: issuers are named for the tenant, and creation is idempotent (ADR-0039 §9) |
| **Corrupt or old backup** | found by the scheduled restore test, not at the bad moment | the same |

**Restoring availability is not restoring trust.** After a compromise, a restored store holds the
compromised keys. A compromise is answered by new CAs, not by a restore.

---

## Consequences

**PKI work needs the operator.** Each meetup or maintenance session starts with an unseal. Nothing
that runs needs it.

**The API needs two credentials and two addresses**, and the PKI one only in a session.

**One more VM to build, patch, back up and restore-test**, and a second backup job.

**The platform store still unseals itself.** A stolen kit still exposes the API's backend
credentials. That is accepted, and recorded, because it holds no CA keys and its secrets can be
rotated.

**ADR-0016's doc drift is corrected on acceptance**: Raft is on the OS disk, `pki/` is retired, and
the API does not use the Go module it names.

---

## Alternatives considered

- **Rejected: one store, sealed by the operator.** Simpler: one instance. But the API cannot start
  until someone unseals it, so every power-on of the kit stops all provisioning. While unsealed, the
  CA keys are as exposed as the platform's secrets for the whole day, not just for a session.
- **Rejected: one store, as today.** CA-making keys unsealed whenever the kit is on, with the seal key
  beside them.
- **Rejected: the PKI keys in ansible-vault as well** (§4).

---

## Open questions

1. **How many unseal shares, what threshold, and where each is kept?**
2. **Where do off-kit backups live**, given that the factory must not depend on the home site? A
   copy there is a backup, not a dependency.
3. **How long is a PKI session?**

---

## What would settle it

V12, V13 and V14 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan).
