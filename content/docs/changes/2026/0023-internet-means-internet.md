---
title: "CHG-0023: Internet Means Internet"
weight: 23
---

# CHG-0023: Internet Means Internet

| | |
|---|---|
| **Date** | 2026-09-23 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | Planned |
| **Window** | 2026-09-23, after the PRs merge. Minutes; one firewall apply |
| **Site** | mobile (the role and home inventory change too; home is not applied) |
| **Systems** | `dv02cor002p01` (core router) |
| **Automation** | `deevnet.net` `opnsense_firewall`: `make migration-opnsense-firewall`, against `ansible-inventory-deevnet/mobile` |
| **Risk** | Low. Seven existing pass rules get narrower; nothing is added or deleted. Most likely to go wrong: a zone that quietly depended on a private address upstream. None is known — nothing in inventory or the roles references one |
| **Related changes** | [CHG-0022](/docs/changes/2026/0022-tenant-dev-network/) (found it), [CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/) (wrote the rule) |
| **Related incidents** | None |
| **Related runbooks** | [Network Segmentation standard](/docs/standards/network-segmentation/) |

---

## Summary

Every zone's internet rule passed to `!10.20.0.0/16`: anything outside the site's own space. That
is not the internet. Guest, and every other internet zone, could reach `192.168.0.0/16` and
`172.16.0.0/12` — confirmed from `DVNTM-TD` in CHG-0022, where the edge router's admin at
`192.168.8.1:80` answered. The standard says guest has *internet access only*.

The value was also hard-coded in the role, so the home site (`10.10.0.0/16`) carried mobile's
range, and its internet rule excluded none of its own segments.

After this change, the internet rule passes to **not `deevnet_private`**, an alias of `10.0.0.0/8`,
`172.16.0.0/12` and `192.168.0.0/16` that the role manages. One rule negates one network, and a
negated list in pf expands into rules that each match everything else; an alias is one table, and
`! <table>` negates the set.

Management and trusted keep the wider rule (`!10.20.0.0/16`), because upstream equipment such as
the edge router is administered from the operator's seats.

## Goal

- Alias `deevnet_private` exists on the router with exactly the three ranges.
- The internet rules of platform, iot, iot_vendor, iot_backend, guest, tenant_dev and
  tenant_transit pass to `!deevnet_private`; management and trusted are unchanged.
- From `DVNTM-TD`: `192.168.8.1:80` times out, the internet still answers, and the CHG-0022 checks
  still pass.
- From a trusted seat: `192.168.8.1:80` still answers.

## Scope

**In scope:** the role (`configure_alias.yml`, the internet rule, defaults), both sites'
`firewall.yml`, one apply on mobile.

**Out of scope:** applying on home; `100.64.0.0/10` and link-local, which are not RFC 1918 and
are not added here.

## Procedure

### Step 1: Plan

```bash
make migration-opnsense-firewall
```

**Verify:** `alias deevnet_private: ADD 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16`, and
ADD 0, UPDATE 7 (each `destination_net: 10.20.0.0/16 -> deevnet_private`), DELETE 0.

### Step 2: Apply

```bash
make migration-opnsense-firewall EXTRA_ARGS="-e firewall_apply=true"
```

The alias is written and loaded first, then the rules. The post-apply checks roll the router back
to the pre-run revision (alias included) if a required path stops answering.

**Verify:** all required paths answer; a re-plan shows the alias matching and 0 / 0 / 0.

**Undo:** revert the role and inventory PRs and apply again. The rules return to `!10.20.0.0/16`; the
alias is left in place, unused.

## Verification

From `DVNTM-TD`, the CHG-0022 script (`chg0022-verify.sh`): 21 passes, and the edge router line
now reads `timeout`. From a trusted seat: `nc -vz 192.168.8.1 80` still succeeds.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ] Apply on home when that site is next built; its internet rules have been wrong since CHG-0007.
