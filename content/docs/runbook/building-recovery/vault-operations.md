---
title: "Vault Operations"
weight: 3
---

# Vault Operations

Ansible Vault protects sensitive variables (passwords, API keys, certificates) stored in the inventory. Each environment has its own set of `vault.yml` files that must be encrypted at rest and decrypted only while editing.

**Repository:** `ansible-inventory-deevnet`

---

## Setup

After cloning the inventory repository, run the one-time hook setup:

```bash
cd ansible-inventory-deevnet
make install-hooks
```

This runs `git config core.hooksPath hooks`, pointing Git at the version-controlled `hooks/` directory. The hooks stay in sync with the repo automatically — no copying required. This must be run once per clone.

---

## Encrypting and Decrypting

### Decrypt all vault files

```bash
make unvault
```

Iterates over every `vault.yml` in the repo and decrypts any that are currently encrypted. Already-decrypted files are skipped.

### Encrypt all vault files

```bash
make vault
```

Iterates over every `vault.yml` in the repo and encrypts any that are currently in plaintext. Already-encrypted files are skipped.

### Typical editing workflow

```bash
make unvault          # decrypt vault files
# edit secrets as needed
make vault            # re-encrypt before committing
git add -u && git commit
```

---

## Pre-commit Guard

The `hooks/pre-commit` script runs automatically on every commit. It checks each staged `vault.yml` file by inspecting the staged blob (`git show ":$file"`), not the working tree. If any staged vault file does not begin with `$ANSIBLE_VAULT`, the commit is rejected with an error message.

If your commit is blocked:

```bash
make vault
git add -u
git commit
```

---

## Vault Files

The following `vault.yml` files exist across the inventory:

| Path | Scope |
|------|-------|
| `mobile/group_vars/all/vault.yml` | Site-wide secrets (mobile) |
| `mobile/group_vars/routers/vault.yml` | Router credentials (mobile) |
| `mobile/group_vars/switches/vault.yml` | Switch credentials (mobile) |
| `mobile/group_vars/network_controllers/vault.yml` | Omada controller credentials (mobile) |
| `mobile/host_vars/hv01/vault.yml` | hv01 secrets (mobile) |
| `mobile/host_vars/hv02/vault.yml` | hv02 secrets (mobile) |
| `home/group_vars/all/vault.yml` | Site-wide secrets (home) |

This list is descriptive, not a definition. `make vault` and `make unvault` discover their targets
with `find . -name 'vault.yml'`, so a new file is picked up without being added here — regenerate
the list with that same command rather than trusting this table to be current.
