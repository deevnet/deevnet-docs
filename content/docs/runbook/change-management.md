---
title: "Change Management"
weight: 6
---

# Change Management & CI/CD

Defines how **change is introduced safely** into the Deevnet ecosystem.

---

## Scope

This section includes:

- Change classification (routine vs disruptive)
- Required validation before changes are applied
- Automated testing expectations by layer
- CI/CD pipeline responsibilities
- Guardrails that prevent unsafe changes from reaching production sites

---

## Principles

Automated testing and CI/CD exist to:

- Validate assumptions early
- Prevent regressions
- Ensure changes preserve correctness

**Manual changes without validation are considered defects.**

---

## Change Classification

| Type | Examples | Validation Required |
|------|----------|-------------------|
| **Routine** | Package updates, config tweaks | Syntax check, dry run |
| **Structural** | New roles, playbook changes | Full test run |
| **Disruptive** | Network changes, storage migration | Staged rollout, backup |

---

## Validation Checklist

Before applying changes:

- [ ] Syntax check passes (`ansible-playbook --syntax-check`)
- [ ] Packer validate passes (for image changes)
- [ ] Dry run shows expected changes (`--check --diff`) — **not available for the network roles, see below**
- [ ] Changes committed to version control
- [ ] Rollback plan documented (for disruptive changes)

{{< hint danger >}}
**`--check --diff` is not a dry run for the network roles.** Neither the OPNsense roles nor
the switch role will show you what a run is about to do — and they fail to in two different
ways.

| Roles | Module | Behaviour under `--check` |
|---|---|---|
| `opnsense_firewall`, `opnsense_dns`, `opnsense_dhcp`, `opnsense_vlans` | `ansible.builtin.uri` | Declares `check_mode: support: none`, so Ansible **skips** every writing task. The run reports nothing pending and no diff, whatever the real run would do — including deletions. |
| `switch_vlans` | `ansible.netcommon.cli_command` | Supports check mode but accepts only `show` commands, so every configuration line **fails**: `Only show commands are supported when using check_mode`. |

The first is the dangerous one, because it is silent: a clean check run reads as "nothing to
change". On 2026-09-07 it preceded the deletion of every firewall rule on the core router and
a total loss of site connectivity — see
[the RCA](/docs/runbook/rca/2026-09-07-firewall-policy-deletion/).

**Validate a network change this way instead:**

1. **Take a config backup first.** These applies are not otherwise reversible.
2. **Read the role's own reporting tasks on a real run.** `Display categorized rules`,
   `Report records that are no longer declared` and their equivalents name what will be added,
   changed and deleted, and they run *before* the writing tasks do.
3. **Confirm the `*_delete_unmanaged` flag is at its default `false`**, so deletions are
   reported and withheld rather than applied. `opnsense_dns` and `opnsense_dhcp` have this
   guard; `opnsense_firewall` does not yet.
4. **Keep console access available** for any change to the core router or to the switch port
   carrying your management path. The automation host sits behind both, so a change that
   severs it also removes your ability to undo it —
   [Console Recovery](/docs/runbook/console-recovery/) is what you follow if it does.
{{< /hint >}}

---

## Status: Planned

CI/CD automation is planned. Current validation is manual.

Future enhancements:

- GitHub Actions for syntax validation
- Automated testing in mobile site
- Promotion workflow (mobile → home)

