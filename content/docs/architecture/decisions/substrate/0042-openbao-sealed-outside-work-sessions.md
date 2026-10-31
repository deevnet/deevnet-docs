---
title: "ADR-0042: OpenBao Sealed Outside Work Sessions"
weight: -42
aliases:
  - /docs/architecture/decisions/substrate/0042-pki-and-platform-secrets-separated/
---

# ADR-0042: The Mobile Factory's OpenBao Is Sealed by Shamir Shares, Opened for a Work Session, and Rebuilt From the Vault

|  |  |
|--|--|
| **Status** | Proposed. Built in part, as of 2026-10-31: §3 ([CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/)) and §4 ([CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)). §1 and §2, the Shamir seal and work sessions, wait on [CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/); see [What would settle it](#what-would-settle-it) and the [decision register](/docs/architecture/reviews/2026-10-tenant-pki/#decision-register) |
| **Date** | 2026-10-21 |
| **Revised** | 2026-10-25, in the [Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/). The draft of 2026-10-21 split OpenBao in two, a platform store that unseals itself and a PKI store on a VM of its own, and recovered the PKI store from snapshots. Both are withdrawn: one OpenBao, sealed, rebuilt from the vault |
| **Scope** | How the Mobile Factory's OpenBao is sealed and opened, what the Deevnet API does while it is sealed, where the keys it uses are authoritatively held, and how it is rebuilt. Not the CA hierarchy ([ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/)) |
| **Amends** | [ADR-0016](/docs/architecture/decisions/substrate/0016-substrate-secrets-openbao/) §2 (the static seal becomes Shamir; the seal key leaves the vault) and §6 (the rebuild order); the [Certificates standard](/docs/standards/certificates/) §5 (where the tenant CA keys are held), once accepted. Extends [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)'s rule (keys held in the vault, imported) to the Tenant Service CA |
| **Resolves** | The conflict between ADR-0016 and [ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/) for OpenBao: once this is built, nothing in OpenBao is kept data |
| **Related** | [ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/), [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/), [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) |

---

## Context

**The Mobile Factory has one OpenBao**, a container on the identity VM beside PowerDNS. Its static
seal key comes from the vault and is written to the same VM, so it unseals at every start with no
operator (ADR-0016 §2). Its data is on the VM's OS disk, with no copy.

**Only the Deevnet API uses it at runtime.** It reads its backend credentials at start and exits if
it cannot; it seals and opens tenant secrets with Transit on tenant requests; it wraps enrollment
tokens; it signs tenant certificates. Devices, the broker, DNS, the log store, Grafana and tenant
workloads never read it. An API outage "stops provisioning, never devices" (ADR-0012).

**Most of what it holds is delivered by Ansible** from the inventory: mounts, policies, AppRoles, the
API's backend credentials. **Three keys are generated inside it and exist nowhere else**: the Transit
key, and the keys of the Tenant Device CA and the Tenant Service CA. CHG-0036 *(Planned)* moves the
Transit key and the Tenant Device CA key into the vault.

**The Mobile Factory travels**, and does its tenant work during visits with the operator present
(ADR-0039).

**Today the API does not tell a sealed store from a lost secret.** A stored tenant secret that will
not open is marked unreadable, so the tenant is told to supply it again; a log token or a dashboard
password that will not open is emptied and re-minted on the next reconcile.

## Decision

### 1. One OpenBao, sealed by Shamir shares

**The static seal becomes Shamir: three unseal shares, any two of which unseal it.** No unseal
material is on the kit. One share is held in the vault; the other two are held apart, encrypted at
rest. **No single machine may hold both the vault password and another share**, because the vault
password opens the vault's share. Every pair is proven at setup by unsealing with it.

**There is no second store.** A store that unseals itself would hold nothing the API needs that the
operator is not there to open.

### 2. It is open for a work session and sealed after

**A work session is a visit's work**: creating a tenant, renewing certificates, enrolling devices,
tenant development. The operator unseals at its start and seals at its end, or the kit powers off.
The API retries until OpenBao opens, as it does today, so no step starts it.

**A sealed OpenBao stops provisioning and nothing else.** Every deployed tenant keeps running.

### 3. A sealed store is unavailable, never a lost secret

**While OpenBao is sealed, the API refuses tenant work before it changes anything**, with an error
that says OpenBao is sealed. It never marks a stored secret unreadable, never empties one, and never
re-mints one because OpenBao is sealed. This is built before the seal changes.

**Ansible plays that configure OpenBao stop with the same plain error** when it is sealed.

### 4. Every key it uses is held in the vault and imported

**The Transit key and both tenant CA keys are generated outside OpenBao, held in the vault, and
imported** on every build, as the Substrate CA's key already is held (ADR-0031 §3). OpenBao is then
a runtime copy of the vault and the inventory.

**The tenant CA keys are replaced once to get there.** They were generated inside OpenBao and
cannot leave it. Each gets a new key made outside, held in the vault, its request signed by the
Mobile Site CA in a ceremony (ADR-0039 §2). Devices trust the root, so none is touched; what the old
keys issued runs to expiry.

**There are no snapshots.** A lost OpenBao is rebuilt: a new store, Shamir setup, everything
imported, the API restarted. Nothing is restored.

**A tenant CA key in the vault is protected by the vault password.** Sealing OpenBao protects the
running kit, but anyone with the vault password can sign. That is already so for the Substrate CA.

### 5. What each failure costs

| Event | Cost |
|---|---|
| **Kit stolen while off, or its disk copied** | None: sealed, and no share on it |
| **Identity VM compromised, sealed** | None readable |
| **Identity VM compromised during a session** | The tenant CA keys and the API's credentials: replace the CA keys, rotate the credentials |
| **OpenBao lost** | Rebuilt from the vault. No device is touched |
| **One share lost or exposed** | None, once the shares are rekeyed with the other two |
| **Two shares lost** | The store is rebuilt from the vault, with new shares |
| **Vault password exposed** | **Every key in the vault, the tenant CA keys among them, is replaced.** A new password alone is not enough: git history keeps the old ciphertext |

---

## Consequences

**Tenant work needs the operator.** Each session starts with an unseal. Nothing that runs needs it.

**The seal key leaves the vault, and the kit holds no unseal material.** Whether OpenBao migrates a
static seal to Shamir in place is to be confirmed when building. If it does not, the store is set
up fresh and imported, which §4 makes routine.

**The vault becomes the one custody of every key OpenBao uses.** Its password, and how it is rotated,
matter more than before.

**CHG-0036 grows** to the Tenant Service CA's key, and both tenant CAs are re-keyed in a ceremony. The Transit key was made non-exportable, so moving
it to the vault means a new key and resealing the stored tenant secrets under it. **Until then the
Transit key exists only inside OpenBao**, and losing OpenBao before CHG-0036 would make every stored
tenant secret unreadable.

**ADR-0016's drift is corrected on acceptance**: its data is on the OS disk, and the API does not use
the Go module it names.

---

## Alternatives considered

- **Withdrawn: two stores, a platform store that unseals itself and a sealed PKI store.** Worth it
  only if the API had to serve tenants with no one present. During visits the operator is there, and
  a self-unsealing store left its seal key on the kit.
- **Withdrawn: the PKI store on a VM of its own.** It protected the store only from a compromise of
  the identity VM during a session, for a VM to build, patch and keep.
- **Withdrawn: snapshots as the recovery path.** A restore on the recovery path, against ADR-0033,
  and one more medium holding secrets.
- **Rejected: keep the static seal.** Every key unsealed whenever the kit is on, with the seal key
  beside it.

---

## Open questions

None.

---

## What would settle it

V12, V13 and V14 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan).
