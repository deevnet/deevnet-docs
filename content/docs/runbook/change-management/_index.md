---
title: "Change Management"
weight: 6
bookCollapseSection: true
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

Classification sets how much validation a change needs. **Change type**, below, says what kind
of change it is. A change has one of each.

---

## Change Types

| Type | Means | Example |
|------|-------|---------|
| **Migration** | Moves a site, service or network from one design to another | [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) flat network → VLANs; [CHG-0003](/docs/changes/2026/0003-host-rename/) host rename |
| **Upgrade** | A new version of software or firmware on an existing system | [CHG-0004](/docs/changes/2026/0004-omada-controller-and-network-firmware/) Omada controller and network firmware |
| **Configuration** | A settings change within the current design | [CHG-0002](/docs/changes/2026/0002-authority-transition-rework/) authority transition rework; moving a switch port from access to trunk |
| **Deployment** | A new system or service brought into service | The MQTT broker VM on IoT Backend |
| **Decommission** | A system or service taken out of service | Dropping the VyOS roles |

---

## Change Records

Every **disruptive** change gets a change record, started before it runs. Structural and
routine changes may have one; otherwise their commit history is their record.

Records are kept under [Change Records](/docs/changes/), numbered `CHG-NNNN` like ADRs, and
start from the [change record template](change-record-template/). The template is maintained
here; each record is retained there. When a change goes wrong in a way that affects service,
the incident gets its own record under [Incident Records](/docs/incidents/) — see
[Incident Management](/docs/runbook/incident-management/).

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
[INC-0001](/docs/incidents/2026/0001-firewall-policy-deletion/).

**Validate a network change this way instead:**

1. **Take a config backup first.** These applies are not otherwise reversible.
2. **Read the role's own reporting tasks on a real run.** `Display categorized rules`,
   `Report records that are no longer declared` and their equivalents name what will be added,
   changed and deleted, and they run *before* the writing tasks do.
3. **Confirm the `*_delete_unmanaged` flag is at its default `false`**, so deletions are
   reported and withheld rather than applied. All three OPNsense roles have this guard:
   `opnsense_dns`, `opnsense_dhcp`, and — since 2026-09-08 — `opnsense_firewall`
   (`firewall_delete_unmanaged`).
4. **Keep console access available** for any change to the core router or to the switch port
   carrying your management path. The automation host sits behind both, so a change that
   severs it also removes your ability to undo it —
   [Console Recovery](/docs/runbook/recovery/console-recovery/) is what you follow if it does.
{{< /hint >}}

---

## Status: Planned

CI/CD automation is planned. Current validation is manual.

Future enhancements:

- GitHub Actions for syntax validation
- Automated testing in mobile site
- Promotion workflow (mobile → home)

