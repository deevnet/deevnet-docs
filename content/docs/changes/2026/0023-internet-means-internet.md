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
| **Status** | **Complete, 2026-09-23.** The router's pf table `deevnet_private` holds the three ranges and seven internet rules negate it. From `DVNTM-TD` the edge router's admin now times out and the internet still answers (21/21); from trusted and management it still answers. |
| **Window** | 2026-09-23 18:50 to 18:51 (apply); client verification afterwards |
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
| before merge | 1 | Plan from the branch: alias ADD, ADD 0, UPDATE 7 (`10.20.0.0/16 -> deevnet_private`), DELETE 0 |
| 18:50 | 1 | The same plan again from `main`, after role #33 and inventory #53 merged |
| 18:50 | 2 | Applied. The alias was saved and loaded with its own reconfigure, then the 7 rules were updated; all 6 required paths still answered, and there was no rollback |
| 18:52 | 2 | pf's table `deevnet_private` (`alias_util/list`): `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`. Re-plan: alias matches, 0 / 0 of 65 / 0 |
| after | Verification | See the table below |

| From | Check | Result |
|---|---|---|
| `DVNTM-TD` (MacBook) | `chg0022-verify.sh` | 21 passed, 0 failed: API, state store, broker TLS and internet still answer, and all 12 internal targets are still blocked |
| `DVNTM-TD` | `192.168.8.1:80` | **timeout**. It was `open` before this change |
| Trusted (a laptop) | edge router admin `192.168.8.1` | reachable (exempt) |
| Management (the Builder) | `192.168.8.1:80`, `https://example.com` | open, 200 (exempt) |

### Departures from the plan

- None to the procedure. Only tenant_dev was tested from a client; guest, iot, iot_vendor, platform
  and tenant_transit carry the same rule change but weren't tested from a client of their own.

## Follow-ups

- [ ] Apply on home when that site is next built; its internet rules have been wrong since CHG-0007.
- [ ] **Home dock mode.** [Naming and Addressing](/docs/architecture/naming-and-addressing/) says a
      docked mobile and home "can communicate with full visibility". Before this change that was true
      only because the internet rule passed to anything outside `10.20.0.0/16`, which let guest reach
      all of home too. Now only management and trusted reach `10.10.0.0/16`. Dock mode isn't in use
      (mobile is behind `dv02edg001p01`). When it is, declare the cross-site flows it needs as zone
      policies, and correct that sentence.
