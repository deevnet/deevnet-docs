---
title: "CHG-0079: The Hypervisors' Notifications From Inventory"
weight: -79
---

# CHG-0079: The Hypervisors' Notifications From Inventory

| | |
|---|---|
| **Date** | 2026-11-21 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **In progress** |
| **Window** | Any time. Nothing restarts; only where the nodes' mail goes changes |
| **Site** | mobile |
| **Systems** | `dv02hyp001p01`, `dv02hyp002p02` |
| **Automation** | `deevnet.builder` `site.yml --limit hypervisors --tags notifications` (the `proxmox_node_notify` role), against `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Most likely to go wrong: no mail arrives, which a test notification shows at once. Undo enables the built-in rule again |
| **Related changes** | [CHG-0042](/docs/changes/2026/0042-rehome-stray-vms/), whose backups mailed the operator by a default no one had set on purpose |
| **Related runbooks** | [Build a Hypervisor](/docs/runbook/substrate/building-recovery/build-hypervisor/) |

---

## Summary

Each hypervisor mails its notifications, such as backup results, failed jobs and package updates,
through Proxmox's built-in target `mail-to-root`. That target sends to whatever address was typed
into the installer. Both nodes happen to have the operator's, but a rebuilt node would mail
whatever was typed that day. This change puts the address and the routing in inventory: an email
target and a rule from the `proxmox_node_notify` role, the address in the vault, and the built-in
rule disabled so each notification is sent once.

## Goal

- Both nodes have the email target `deevnet-operator`, sending to the vault's address from
  `root@<node FQDN>`, and the rule `deevnet-all` sending every notification to it.
- Proxmox's built-in `default-matcher` is disabled on both.
- A test notification from each node arrives.
- *Build a Hypervisor* says the node's notifications come from inventory.

## Scope

**In scope:** the notification target and rules on both hypervisors.
**Out of scope:** what Proxmox notifies about; Postfix, which still sends the mail directly; root's
own email address, which nothing routes to once the built-in rule is off.

## Prerequisites

- [ ] `deevnet.builder`: the `proxmox_node_notify` role
- [ ] `ansible-inventory-deevnet`: `proxmox_node_notify_email` for the hypervisors, and
  `vault_proxmox_notify_email` in the site's vault

## Procedure

### Step 1: Check

```bash
ansible-playbook playbooks/site.yml --limit hypervisors --tags notifications --check
```

### Step 2: Apply

```bash
ansible-playbook playbooks/site.yml --limit hypervisors --tags notifications
```

A second run changes nothing.

### Step 3: Test

On each node: **Datacenter → Notifications**, select `deevnet-operator`, **Test**. Or
`pvesh create /cluster/notifications/targets/deevnet-operator/test`.

## Verification

Both nodes list `deevnet-operator` and `deevnet-all`, `default-matcher` is disabled, and each
node's test mail arrives from `root@<node FQDN>`.

## Undo

On each node, enable `default-matcher` again and remove `deevnet-all` and `deevnet-operator`:

```bash
pvesh set /cluster/notifications/matchers/default-matcher --disable 0
pvesh delete /cluster/notifications/matchers/deevnet-all
pvesh delete /cluster/notifications/endpoints/sendmail/deevnet-operator
```

## To close

- [ ] Step 2: applied to both nodes, and a second run changes nothing
- [ ] Step 3: a test mail from each node arrives
- [ ] Verification passes
