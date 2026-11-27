---
title: "SSH Host Keys"
weight: 7
---

# SSH Host Keys

**Every substrate host's SSH host keys are recorded in git, and the builders trust that record.**
The record is `ssh/mobile/known_hosts` in `ansible-inventory-deevnet`. It lists each host by
inventory name, FQDN and the address Ansible uses. The `ssh_known_hosts` role in `deevnet.builder`
installs it on both builders as `/etc/ssh/ssh_known_hosts`. Every SSH client there reads that file
beside the user's own `known_hosts`. So a repaved builder knows every host without learning a key
again, and so do the operator's scripts that reach a host by name, such as `make reconcile`
([CHG-0099](/docs/changes/2026/0099-host-keys-in-git/)).

| | |
|---|---|
| The record | `ansible-inventory-deevnet/ssh/mobile/known_hosts` (`site_ssh_known_hosts_file`) |
| Installed on | `builder`: `dv00bld001p01`, `dv02bld001v01` |
| Installed by | `deevnet.builder` `site.yml`, tag `host_keys`; on its own, `make host-keys-install` |
| Updated by | `make host-keys LIMIT=<host>` in `deevnet.builder`, then a pull request in the inventory |
| Not covered | Ansible itself: every collection sets `host_key_checking = False`. Checking every host from every play is the host-certificates item on the [Security Hardening](/docs/roadmap/infrastructure/substrate/security-hardening/) roadmap |

---

## A host is built or rebuilt

**A rebuilt host has new keys, so SSH to it by name fails until the record has them.** That is the
point of the record: a host whose identity changed is noticed, not trusted.

1. **Scan its keys into the record**, from `deevnet.builder` on the Builder:

   ```bash
   make host-keys LIMIT=<host>
   ```

   The play writes only the inventory's file. It prints each host as `new`, `CHANGED` or `unchanged`,
   with the fingerprints of every key added or removed. A host that serves no key keeps its lines,
   and the play fails.

2. **Open a pull request in the inventory** with the changed `ssh/mobile/known_hosts`. Its review
   checks that the host was really rebuilt, and that the new fingerprints are the host's. Its
   console prints them with `ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`.

3. **After the merge, install it on the builders:** `make host-keys-install`.

4. **Remove any old key from your own `known_hosts`** (`ssh-keygen -R <name>`, and the same for its
   address). A stale key there makes SSH refuse the host even though the system file is right.

## A host is retired

Delete its lines from the record in the same pull request that moves it to `inactive`, and run
`make host-keys-install` after the merge
([Inventory Lifecycle](/docs/runbook/substrate/lifecycle/inventory-lifecycle/)).

## A builder is repaved

Nothing to do. `site.yml` installs the record with the rest of the builder configuration
([Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/), Step 4).

## Hosts without keys in the record

- `dv02wap001p01`: no SSH.
- `dv02rpi001p01` and `dv02rpi003p01`: powered off at the first scan. Run
  `make host-keys LIMIT=<pi>` when one is next on.
