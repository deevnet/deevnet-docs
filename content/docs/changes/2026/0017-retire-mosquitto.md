---
title: "CHG-0017: Retire Mosquitto"
weight: 17
---

# CHG-0017: Retire Mosquitto

| | |
|---|---|
| **Date** | TBD |
| **Change type** | Configuration · Cleanup |
| **Classification** | Routine |
| **Status** | **Planned.** Smaller than it was scoped to be — see *What changed under this record*. |
| **Window** | TBD |
| **Systems** | Inventory and the `deevnet.mgmt` collection only. **No host is touched, and no service restarts.** |
| **Automation** | None to run. This is a deletion, verified by a play that already ignores what is being deleted. |
| **Risk** | Low — everything removed is read by nothing. The one care point is a vault file, if it turns out to hold anything. |
| **Related changes** | [CHG-0015](/docs/changes/2026/0015-vernemq-broker/) (replaced the broker), [CHG-0016](/docs/changes/2026/0016-broker-accounts/) (replaced the ACLs) |
| **Related incidents** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) — why a vault edit gets its own ordering |

---

## Summary

The pivot from Mosquitto to VerneMQ left litter in three places. None of it is read by
anything, and all of it describes a broker that no longer exists.

This is **deletion, not migration**. That distinction is the whole reason this record is
smaller than the follow-up that proposed it.

## What changed under this record

This was planned while `lightd` and `lp-stand-01` still had nowhere else to live, and the
working plan for it was *migrate those permissions out of inventory into tenant Terraform*.

**That migration is already done.** EdS declares both accounts in its own Terraform as
`deevnet_iot_broker_account` resources, with the same permissions, merged before this record
was written. What remains in inventory is not the source of anything — it is a copy that
stopped being read when the `mosquitto` role stopped running.

So this record does not move permissions. It deletes the copies. CHG-0016's own follow-up had
already reached the same conclusion, calling them *"orphaned, not merely debt"*; this record
is where that is acted on.

## What is removed

| | Where | Read by |
|---|---|---|
| `mqtt_acls` | `mobile/group_vars/mqtt_brokers/vars.yml` | the `mosquitto` role, and nothing else |
| `vault_mqtt_users` | a vault file, **if it is still anywhere** — see below | the same |
| The `mosquitto` role | `deevnet.mgmt/roles/mosquitto/` | no playbook |
| One README line | `deevnet.mgmt/README.md` | people |

### Why this is safe

**`mqtt_acls` and `vault_mqtt_users` are orphaned, not debt.** The only consumer was the
`mosquitto` role:

```
roles/mosquitto/defaults/main.yml:43: mosquitto_users: "{{ vault_mqtt_users | default({}) }}"
roles/mosquitto/defaults/main.yml:51: mosquitto_acls:  "{{ mqtt_acls | default({}) }}"
```

and **no playbook runs that role**. `site.yml`'s MQTT play runs `vernemq` (CHG-0015). So these
variables describe accounts that do not exist, on a broker that never sees them, for a role
nothing invokes. Deleting them changes no rendered configuration anywhere.

**The README line is worse than nothing.** It still says the `mosquitto` role is *"to be
replaced by VerneMQ in the messaging VM."* It has been. A document describing a future that
already happened sends a reader looking for work that is finished.

**`dv02mqt001v01` needs nothing.** It is already out of inventory and named only in a comment.

### The one thing to confirm in the window

**Whether `vault_mqtt_users` still exists at all.** With the inventory decrypted earlier,
`mobile/group_vars/mqtt_brokers/vault.yml` held four `vault_vernemq_*` keys and no
`vault_mqtt_users` — so it is not there. Whether it survives in another vault file has **not**
been established, because a grep over an encrypted file matches ciphertext and proves nothing
either way.

Check it while the inventory is unvaulted, at the start of the window. If it is gone, this
change touches no vault file at all and the ordering below does not apply.

## Procedure

1. `make unvault`, and **first** confirm whether `vault_mqtt_users` exists anywhere.
2. Delete `mqtt_acls` from `mobile/group_vars/mqtt_brokers/vars.yml`, and the comment above it
   that refers to `vault_mqtt_users`.
3. Delete `vault_mqtt_users` **only if step 1 found it**.
4. Delete `roles/mosquitto/` from `deevnet.mgmt`.
5. Correct the collection README's role table.
6. `make vault`, commit, and **push** — in that order, before anything is deleted from a
   working copy. This is the ordering [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/)
   exists to enforce: a vault file that is edited and not pushed is how that incident started.
   It applies here only if step 3 ran.

## Verification

| Check | Expect |
|---|---|
| `ansible-playbook playbooks/site.yml --syntax-check` | passes — nothing referenced the role |
| `site.yml --limit mqtt_brokers` | runs `vernemq`, unchanged, and reports the same broker state |
| `grep -r mqtt_acls` over the collections | no hits |
| The broker's account count | **unchanged** — this touches no host |
| A client with an issued account | still connects, publishes in its ACL, is refused outside it |

The last two are the ones that matter. If either changes, something was reading the deleted
values after all, and the deletion should be reverted before anything else is investigated.

## Undo

`git revert`. Nothing is applied to a host, so there is no state to restore — with the single
exception of a vault edit, which is why step 6 pushes before deleting.

## Follow-ups

- **`mqtt01` survives in three source files** in the EdS repository as comments —
  `services/lightd/internal/broker/broker.go`, `services/lightd/internal/config/config.go`
  and `firmware/lp-stand/main/network/mqtt/mqtt.h`. The name does not resolve and appears
  never to have. The READMEs were corrected alongside EdS's broker accounts; these were left
  because they are application source rather than documentation.
- **The API does not issue the broker's hostname.** Every other substrate value a tenant uses
  — the DNS server, the state endpoint, the Wi-Fi SSID — comes back from the API precisely so
  a tenant need not hardcode it. EdS has to name `mqtt.mobile.deevnet.net` in a variable.
  Worth closing, so that moving a tenant between sites stays an API concern.
