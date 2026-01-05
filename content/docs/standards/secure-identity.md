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
Host vdvntm-* dvntm*
    HostName %h.dvntm.deevnet.net
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
Private keys MUST remain on the client.

- use SSH agents
- use forwarding only to systems you control and trust
- prefer short-lived credentials when available

Example concept:
```sshconfig
Host *.dvntm.deevnet.net
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
Host vdvntm-* dvntm*
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

## 5. Definition of “Secure” (for Deevnet Client Access)

Deevnet client access is **secure** when:

- SSH access works using DNS names without per-host client edits
- private keys remain on the client; authentication uses agents/certs
- secrets are not pasted, exported manually, or stored in plaintext files
- IaC contains references to secrets, not the secrets themselves
- access can be revoked without hunting through laptops and scripts
- the “right way” is the easiest way

If secure access is the default path of least resistance, the system is secure.

---
