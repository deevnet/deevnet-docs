---
title: "CHG-0099: The Site's SSH Host Keys Recorded in Git"
weight: -99
---

# CHG-0099: The Site's SSH Host Keys Recorded in Git

| | |
|---|---|
| **Date** | 2026-11-27 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **In progress**: started 2026-11-27 |
| **Window** | No outage. One file is written on each builder |
| **Site** | mobile |
| **Systems** | `dv00bld001p01`, `dv02bld001v01`; the inventory's new `ssh/mobile/known_hosts` |
| **Automation** | `deevnet.builder`: the `ssh_known_hosts` role in `site.yml` (tag `host_keys`); `make host-keys` and `make host-keys-install` |
| **Risk** | Low. Most likely to go wrong: a wrong key in the record makes SSH to that host fail by name; it is found by the check in Step 3 and undone by removing the file |
| **Related changes** | [CHG-0098](/docs/changes/2026/0098-vm-builders-apply-profile/), whose follow-up this is; [CHG-0092](/docs/changes/2026/0092-builder-repave-f44/), the repave that lost the keys |
| **Related runbooks** | [SSH Host Keys](/docs/runbook/substrate/lifecycle/host-keys/), new; [Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/) |

---

## Summary

**The repaved Builder knew substrate hosts' SSH keys by address only, so `make reconcile` failed to
reach the API host by name** (CHG-0098). Ansible had recorded the addresses as it connected. It does
not check host keys, so it never noticed the names were missing.

**The keys go into git, and the builders trust that record.** The inventory gets
`ssh/mobile/known_hosts`, listing every host by name, FQDN and address. The new `ssh_known_hosts`
role installs it on both builders as `/etc/ssh/ssh_known_hosts`. A repave then needs nothing copied
by hand. A rebuilt host's new keys arrive by `make host-keys` and a pull request, so a host whose
identity changed is reviewed, not trusted. Ansible's own connections are unchanged; checking those is
the host-certificates item on the
[Security Hardening](/docs/roadmap/infrastructure/substrate/security-hardening/) roadmap.

## Goal

From either builder, with no user `known_hosts` at all, SSH by name and by address to every host in
the record is checked and connects.

## Scope

**In scope:**

| Repository | Pull request | What |
|---|---|---|
| `ansible-inventory-deevnet` | [#138](https://github.com/deevnet/ansible-inventory-deevnet/pull/138) | The record, seeded as below; `site_ssh_known_hosts_file` |
| `deevnet.builder` | [#63](https://github.com/deevnet/ansible-collection-deevnet.builder/pull/63) | The `ssh_known_hosts` role, in `site.yml` for `builder`; `playbooks/host-keys.yml` and `scripts/host-keys-merge`; `make host-keys`, `make host-keys-install` |
| `deevnet-docs` | | This record; the [SSH Host Keys](/docs/runbook/substrate/lifecycle/host-keys/) runbook, linked from the repave, VM build, restore and retirement runbooks |

**Out of scope:** Ansible's `host_key_checking`; the update watcher's own `known_hosts` (it pins its
own keys).

## The seed

**Every key was scanned from its host on 2026-11-27, and the record is what the scan returned.**
Most were also checked against two earlier records:

| Hosts | Checked against |
|---|---|
| `dv00bld001p01`, `dv02bld001v01`, the two hypervisors, and the seven service VMs | The Builder's `known_hosts` and the standby builder's, last written 2026-11-25, before the repave. All match |
| `dv02acc001p01` (the switch) | Only answers a scan for its one type (RSA), so its key is the one both builders already held. They agree |
| `dv02cor002p01`, `dv02edg001p01` (the routers), `dv02rpi002p01`, `dv02rpi004p01` | Nothing: neither builder had them. **First recorded by this scan**; their fingerprints can be checked at the console |
| `dv02wap001p01`; `dv02rpi001p01`, `dv02rpi003p01` | Not in the record: no SSH; powered off |

## Risk and impact

| Risk | Mitigation |
|---|---|
| A key in the record is wrong, so SSH to that host by name fails | Every key is what the host served on 2026-11-27, and most match the pre-repave records. Step 3 checks every host. Undo: remove `/etc/ssh/ssh_known_hosts` |
| A user's own `known_hosts` has a stale key the record does not, and SSH refuses | `ssh-keygen -R` that entry, as the runbook says |
| `make host-keys` drops a host that is down | A host that serves no key keeps its lines, and the play fails (tested) |

## Procedure

### Step 1: Merge the code

**Run:** review and merge the three pull requests; `make publish` in `deevnet.builder`.

**Verify:** `make check` passes.

### Step 2: Install the record on the builders

**Run:** `make host-keys-install` in `deevnet.builder`.

**Verify:** `/etc/ssh/ssh_known_hosts` on both builders is the inventory's file.

### Step 3: The check

**Run,** on each builder, for every host in the record, by name, FQDN and address:

```bash
ssh -o UserKnownHostsFile=/dev/null -o BatchMode=yes a_autoprov@<host> true
```

**Verify:** every host connects, its key checked against the system file alone. Then the line added
to the operator's `known_hosts` by hand for `dv02prv001v01` in CHG-0098 is removed, and
`make reconcile NAME=tdemo` still works.

## Undo

Remove `/etc/ssh/ssh_known_hosts` from both builders and revert the pull requests.

## To close

**This change closes when every item below is done.**

- [ ] Step 1: the three pull requests merged
- [ ] Step 2: the record installed on both builders
- [ ] Step 3: every host checked by the system file alone; the hand-added line gone

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| Before Step 1 | Tests | `make host-keys` against a copy of the seed: every host `unchanged`, the three with no key reported and kept, the file identical. One key altered: `CHANGED`, with its old and new fingerprints, and put right. The role in check mode: would install on both builders |

### Departures from the plan

None yet.
