---
title: "Console Recovery"
weight: 7
---

# Console Recovery

Getting back into the core router when the network cannot reach it — and restoring the
configuration that locked you out.

{{< hint danger >}}
**This is the only way back when the firewall policy is wrong.** The management path to
`dv02cor002p01` is itself a rule on `dv02cor002p01`. Delete or break the anti-lockout rules
and the web UI, the API and SSH all go with them; the automation host sits behind the same
policy, so it cannot undo its own change either. When that happens there is no remote
option left, only this page.

This is not hypothetical — it happened on 2026-09-07. See
[the RCA](/docs/runbook/rca/2026-09-07-firewall-policy-deletion/).
{{< /hint >}}

---

## What you need

| | |
|---|---|
| **Cable** | Mini DisplayPort → your monitor. The box has no VGA or HDMI. |
| **Keyboard** | USB. |
| **Access** | Physical, at `dv02cor002p01`. |
| **Backup** | None to carry — OPNsense keeps its own config history on the box. |

Keep the mini DisplayPort cable somewhere you will find it in the dark. It is an unusual
connector and it is only ever needed on the worst day.

---

## 1. Confirm it is actually the router

A trip to the rack is worth thirty seconds of triage first. From a host on the management
segment:

```bash
ping -c1 10.20.99.1                                  # the router's LAN address
timeout 3 bash -c 'exec 3<>/dev/tcp/10.20.99.1/443'  # web UI
timeout 3 bash -c 'exec 3<>/dev/tcp/10.20.99.1/22'   # ssh
```

| Symptom | Likely cause |
|---|---|
| Gateway answers, 443 and 22 both refused | **Firewall policy.** The anti-lockout rules are gone. This page. |
| Nothing answers, from any segment | Router down, or its LAN port/trunk. This page. |
| Same-segment works, cross-segment does not | Zone policy, not lockout. Still needs the console if the API is unreachable. |
| Only one segment is affected | Switch port or VLAN, not the router — see [network segmentation troubleshooting](/docs/runbook/network-migration/troubleshooting/). |

{{< hint warning >}}
**A gateway that answers ICMP proves nothing about the policy.** The router replies on its
own interface addresses regardless of whether any transit rule survives. During the
2026-09-07 incident all four segment gateways answered while every inter-VLAN rule was
already deleted. Test the ports and a cross-segment host, not just the gateway.
{{< /hint >}}

---

## 2. Get a console

Mini DisplayPort to the monitor, USB keyboard, and the console menu is on screen. If the
menu is password-protected you will need the root password from the inventory vault
(`mobile/group_vars/routers/vault.yml`) — decrypt it **before** you walk over, since the
vault lives on a host you may no longer be able to reach.

---

## 3. Restore the configuration

OPNsense keeps a history of previous configurations on the box itself, in `/conf/backup/`,
one entry per change with a timestamp and a description. Nothing needs to be carried in.

From the console menu, choose **Restore a backup**.

{{< hint info >}}
**Read the menu, do not trust the number.** It is option `13` on current builds, but the
numbering has shifted between releases and the entry you want is named, not numbered.
{{< /hint >}}

Pick the last revision **before** the change that caused the outage. The descriptions carry
what changed, which is usually enough to identify it; when in doubt go further back — a
slightly stale configuration that routes is worth more than a current one that does not.

The router applies the configuration and restarts services. Give it a minute.

---

## 4. Verify

From a host on the management segment:

```bash
timeout 3 bash -c 'exec 3<>/dev/tcp/10.20.99.1/443' && echo "web UI back"
ping -c1 10.20.30.11        # a host on another segment - transit policy
ping -c1 1.1.1.1            # egress
```

And on the console itself, option **Shell**, to see the live ruleset rather than what the
GUI believes:

```sh
pfctl -sr | grep -c .       # rules actually loaded
pfctl -sr | grep anti-lock  # the rules that let you back in remotely
```

Do not leave the rack until a cross-segment ping works. The gateway answering is not the test.

---

## 5. Reconcile afterwards — a restore rolls back everything

This is the step that gets forgotten. A config restore reverts the **whole** of
`config.xml` to that point in time, not just the part that broke: DHCP reservations,
Unbound host overrides and aliases, interface assignments, VLANs, NAT — every change
applied since that revision, including legitimate ones.

Inventory is the source of truth, so re-run the roles to bring the router back up to
declared state:

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/dns.yml          # Unbound records
ansible-playbook playbooks/dhcp.yml         # Kea reservations
```

Read the reporting tasks in the output rather than trusting `changed=0` — and see
[Change Management](/docs/runbook/change-management/) first, because `--check --diff` will
not preview any of it.

{{< hint warning >}}
**Do not re-run `opnsense_firewall` to "put the rules back".** Until the guards from the
RCA's corrective actions land, that role is capable of deleting the policy again, and a
degraded discovery is exactly what it does when something upstream has changed. Restore the
rules by config restore, not by reconvergence.
{{< /hint >}}

---

## Known gap: the backup only lives on the box

There is no off-box config backup automation anywhere in the collections. OPNsense's local
history is what saved 2026-09-07, and it is enough for a policy mistake — but it is on the
router, so it does not survive a failed disk or a box that will not boot.

The manual step exists and is already in the
[segmentation prerequisites](/docs/runbook/network-migration/prerequisites/): **System →
Configuration → Backups → Download**. Take one before any disruptive change to the router,
and keep it somewhere that is not the router.

---

## Related

- [RCA: 2026-09-07 firewall policy deletion](/docs/runbook/rca/2026-09-07-firewall-policy-deletion/) — why this page exists
- [Change Management](/docs/runbook/change-management/) — what actually validates a network change
- [Network segmentation troubleshooting](/docs/runbook/network-migration/troubleshooting/) — switch console, VLAN and DHCP faults
