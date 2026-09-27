---
title: "Change Management"
weight: 2
bookCollapseSection: true
---

# Change Management

How to make a change to the substrate: pick its type, open a record if it needs one, validate it,
and lock in anything it generates. When a change needs a record, and how much validation it needs,
is set by the [Change Management](/docs/policies/change-management/) policy.

To open a record, copy the [change record template](change-record-template/).

---

## Change types

| Type | Means | Example |
|------|-------|---------|
| **Migration** | Moves a site, service or network from one design to another | [CHG-0001](/docs/changes/2026/0001-flat-network-to-vlans/) flat network → VLANs; [CHG-0003](/docs/changes/2026/0003-host-rename/) host rename |
| **Upgrade** | A new version of software or firmware on an existing system | [CHG-0004](/docs/changes/2026/0004-omada-controller-upgrade/) Omada controller 6.1 → 6.3; [CHG-0006](/docs/changes/2026/0006-access-switch-firmware-upgrade/) switch firmware |
| **Configuration** | A settings change within the current design | [CHG-0002](/docs/changes/2026/0002-authority-transition-rework/) authority transition rework; moving a switch port from access to trunk |
| **Deployment** | A new system or service brought into service | The MQTT broker VM on IoT Backend |
| **Decommission** | A system or service taken out of service | Dropping the VyOS roles |

A change has one type and one classification; the classification sets how much validation it needs
([policy](/docs/policies/change-management/#change-classification)).

---

## Validation checklist

Before applying changes:

- [ ] Syntax check passes (`ansible-playbook --syntax-check`)
- [ ] Packer validate passes (for image changes)
- [ ] Dry run shows expected changes (`--check --diff`) — **not available for the network roles, see below**
- [ ] Changes committed to version control
- [ ] Rollback plan documented (for disruptive changes)
- [ ] **Any once-only secret the change produces is encrypted, committed and pushed before the
      change continues** — see [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/)

{{< hint warning >}}
**A secret a change generates is not safe until it is pushed.** An OpenBao init, a device token a
vendor shows once, a Proxmox token secret: while it sits in a decrypted `vault.yml` it exists in one
place that git is configured to reject, so nothing is holding it. Encrypt, commit and push it, and
only then delete whatever the change wrote it to.

While the inventory is decrypted, `git reset --hard`, `git restore .` and `git clean -fd` destroy
plaintext with no way back — it was never staged, so it is not in the object database. CHG-0010 lost
OpenBao's recovery key and Ansible's AppRole that way and had to rebuild the service.
[Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/) has the procedure.
{{< /hint >}}

{{< hint danger >}}
**`--check --diff` is not a dry run for the network roles.** Neither the OPNsense roles nor
the switch role will show you what a run is about to do — and they fail to in two different
ways.

| Roles | Module | Behavior under `--check` |
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
   `opnsense_dns`, `opnsense_dhcp` and `opnsense_firewall` (`firewall_delete_unmanaged`).
4. **Keep out-of-band access available** for any change to the core router or to the switch port
   carrying your management path — the router's console, and for the switch, which has no
   console port, the reset button and a laptop. The automation host sits behind both, so a change that
   severs it also removes your ability to undo it —
   [Console Recovery](/docs/runbook/substrate/recovery/console-recovery/) is what you follow if it does.
{{< /hint >}}
