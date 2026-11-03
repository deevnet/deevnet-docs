---
title: "Secure Identity"
weight: 2
---

# Deevnet Secure Identity Standard

### Purpose
This document defines what it means for **Deevnet client access to be secure**.

Secure identity is not defined by whether you can “SSH in,” but whether access:
- minimizes secret exposure,
- is reproducible across devices and OSes,
- supports least privilege and revocation,
- and avoids habits that don’t scale beyond a lab.

This document captures the **intent, principles, and invariants** of secure client identity and access in Deevnet.

---

## 1. Foundational Principles

### 1.1 Identity Is Long-Lived; Credentials Are Short-Lived
Clients MAY hold long-lived **identity** material (e.g., SSH private keys).  
Everything else should trend short-lived:

- short-lived certificates over static keys (where feasible)
- short-lived tokens over static API keys
- secrets fetched **just-in-time** over secrets stored on disk

If compromise of a single laptop exposes long-lived secrets, the design is incorrect.

---

### 1.2 Clients Hold Identity, Not Secrets
A client device is allowed to prove *who you are* — it should not permanently store *what you know*.

**Allowed on clients**
- SSH keys and agent state
- OS-backed secure storage (Keychain / Credential Manager)
- configuration that references secret locations (paths), not secret values

**Incorrect on clients**
- `.env` files with real credentials
- plaintext secrets in scripts, notes, or repos
- long-lived API keys copied around “for convenience”

---

### 1.3 No Copy/Paste Secrets as a Workflow
Copy/paste is a leakage engine.

- it creates untracked exposure
- it normalizes unsafe habits
- it leads to shell history, scrollback, and logging leaks

If a workflow requires manually pasting secret material, it is considered incorrect.

---

### 1.4 Names Over Addresses (Client Access)
Hostnames are the interface; IPs are plumbing.

- Clients MUST prefer DNS names to avoid per-host client configuration drift
- If an IP changes and clients must be edited, correctness is violated

Example concept (DNS-driven access):
```sshconfig
Host dv02*
    HostName %h.mobile.deevnet.net
```

---

## 2. Identity vs Access vs Secrets (Separation of Concerns)

### 2.1 Identity
Identity answers: **who is this user/device?**

Examples:
- SSH keypair (client identity)
- hardware-backed key storage (where applicable)

### 2.2 Access
Access answers: **what systems may this identity reach and what may it do?**

Examples:
- SSH authorization on hosts
- bastion / jump paths
- role-based privileges on target systems

### 2.3 Secrets Delivery
Secrets delivery answers: **how do tools/apps obtain sensitive values without persisting them?**

Examples:
- session-scoped injection
- broker-issued short-lived tokens
- agent-based delivery

If one layer must “reach across” to do another layer’s job, the design is incorrect.

---

## 3. SSH Identity Invariants

### 3.1 Private Keys Do Not Move
Private keys MUST remain on the client. The same holds for every X.509 key, a device's included:
[Certificates](/docs/standards/certificates/) says where each may live.

- use SSH agents
- use forwarding only to systems you control and trust
- prefer short-lived credentials when available

Example concept:
```sshconfig
Host *.mobile.deevnet.net
    ForwardAgent yes
```

---

### 3.2 SSH Config Is Declarative and Compact
Client access configuration MUST be:
- declarative
- reproducible
- OS-portable where possible

Avoid “one host = one stanza” unless you need a true exception.

Example concept (wildcards + shared settings):
```sshconfig
Host dv02* dv00*
    User cdeever
    IdentityFile ~/.ssh/id_ed25519
    ForwardAgent yes
```

---

## 4. Secrets Handling Invariants

### 4.1 Environment Variables Are Delivery, Not Storage
Environment variables MAY be used to *deliver* secrets to a process, but SHOULD NOT become a manual storage method.

Incorrect:
```bash
export DB_PASSWORD="paste-secret-here"
```

Correct concept: secrets are injected **ephemerally** for a single process or subshell (broker is a placeholder):
```bash
broker exec apps/foo -- make deploy
```

---

### 4.2 Secrets Must Be Session-Scoped (or Process-Scoped)
Secrets should exist:
- only for the duration of a single command, or
- only inside a short-lived subshell

If secrets persist across terminal sessions by default, the design is incorrect.

---

### 4.3 No Secrets in Infrastructure-as-Code
IaC MUST reference secret *locations*, not secret *values*.

Incorrect:
```yaml
db_password: "hunter2"
```

Correct concept:
```yaml
db_password_path: "secret/apps/foo/db_password"
```

---

### 4.4 IaC Source and IaC State Are Different Things

§4.3 governs IaC **source** — the `.tf`, `.tfvars` and playbook files a human writes. Terraform
**state** is not source. It is the record of an apply, written by the tool, and it can contain
attribute values that were never typed into any file.

That distinction matters because the protection is different in kind. Source is protected by review:
a secret in a `.tf` is visible in a diff. State is protected by nothing — it is machine-generated,
rarely read, and a provider that decides to persist an attribute will do so silently on the next
apply.

The invariant:

> **The moment state contains a secret value, whatever holds that state becomes a secret store.**

So a repository holding state is a secret store, and a bucket holding state is a secret store, and
both must be treated as one. Two rules follow:

- **Prefer resources whose values can be re-derived.** A declaration that generates a credential
  puts that credential in state permanently. Issue credentials out of band and reference them.
- **Do not assume state is clean because it is clean today.** Whether a given provider persists a
  sensitive attribute is that provider's implementation detail, and it can change under a version
  bump with nothing in the configuration changing at all.

Where Deevnet's own state lives, and what enforces this, is
[ADR-0007](/docs/architecture/decisions/tenant-model/0007-terraform-state-custody/).

---

## 5. Exposed Credentials

### 5.1 What Counts as Exposed
**A credential is exposed when a copy may exist anywhere it was not issued to.** Whether anyone
has used the copy does not matter. Each of these makes a credential exposed:

- it was committed or pushed unencrypted, to any repository, even if the commit was reverted or
  the history rewritten
- it was printed, pasted or written outside the vault and the systems it was issued to: a
  terminal, a log, a CI job's output, a chat transcript, a ticket, a document or a screenshot,
  even if everyone who could see it was trusted
- the secret scan on a repository flagged it ([CHG-0035](/docs/changes/2026/0035-exposed-credentials/))
- a disk or device that held it was lost, stolen, or left Deevnet's hands without being wiped
- a person who knew it no longer has a role that needs it
- a host that held it was compromised, or might have been

Not knowing whether a credential was exposed counts as exposed.

### 5.2 How Soon
**An exposed credential is rotated now if a copy may have left Deevnet, and at the next rebuild if
it did not.** A copy has left Deevnet when it reached a public repository, anyone outside the
operators, an outside service (a chat, a CI provider's logs), lost hardware or a compromised host.
Rotate those at once. A copy that stayed on Deevnet's own systems and in front of its own
operators, such as a value printed to the operator's terminal or a substrate host's log, may wait
for the next rebuild or rotation of what it unlocks. Either way the exposure is recorded, and the
copy is removed where it can be.

### 5.3 What Happens Next
**An exposed credential is rotated first and investigated after.** Rewriting history or deleting
the copy is not a fix: copies may already exist elsewhere, so only replacing the credential ends
the exposure.

1. **Rotate it**, with its procedure in the [Credential Rotation](/docs/roadmap/infrastructure/substrate/credential-rotation/plan/)
   plan's list if there is one. Change it on the system that accepts it, then in the vault, then
   on every consumer the list names, and confirm the automation that uses it still works.
2. **Record the rotation as a change** ([Change Management](/docs/policies/change-management/)),
   naming the credential, never its value. Several credentials exposed together get one record, as
   CHG-0035 did.
3. **Write the procedure if it had none.** The rotation just done becomes that credential's
   procedure, in the same change, and the Credential Rotation list says so.
4. **Open an incident** ([Incident Management](/docs/policies/incident-management/)) if the
   credential was used by someone it was not issued to, or if rotating it cost service.
5. **If it cannot be rotated yet**, record it in the
   [risk register](/docs/policies/risk-management/risk-register/) with what it reaches and what
   would let it be rotated. Treat it as exposed until it is.

A credential shared with a tenant is rotated with that tenant: the operator issues the new value,
the tenant takes it up, and the old value is revoked once both sides have moved.

---

## 6. Definition of “Secure” (for Deevnet Client Access)

Deevnet client access is **secure** when:

- SSH access works using DNS names without per-host client edits
- private keys remain on the client; authentication uses agents/certs
- secrets are not pasted, exported manually, or stored in plaintext files
- IaC contains references to secrets, not the secrets themselves
- access can be revoked without hunting through laptops and scripts
- the “right way” is the easiest way

If secure access is the default path of least resistance, the system is secure.

---
