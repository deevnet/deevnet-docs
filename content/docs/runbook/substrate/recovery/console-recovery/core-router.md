---
title: "Core Router"
weight: 1
aliases:
  - /docs/runbook/recovery/console-recovery/core-router/
  - /docs/runbook/console-recovery/core-router/
---

# Core Router

Recovering `dv02cor002p01` from the physical console when the network cannot reach it, and
restoring the configuration that closed the door.

The router's management path — the web UI, the API, SSH — is itself a firewall rule on the
router. When that rule is wrong there is no remote route back in, including for the
automation host, which sits behind the same policy and so cannot undo its own change. The
console is the way in.

## What you need

| | |
|---|---|
| **Cable** | Mini DisplayPort → your monitor. The box has no VGA or HDMI. |
| **Keyboard** | USB. |
| **Access** | Physical, at `dv02cor002p01`. |
| **Backup** | None to carry — OPNsense keeps its own config history on the box. |

Decrypt the vault **before** you walk over if the console menu is password-protected. The
root password is in `mobile/group_vars/routers/vault.yml`, on a host you may no longer be
able to reach.

---

## 1. Confirm it is the router

A trip to the rack is worth thirty seconds of triage. From a host on the management segment:

```bash
ip neigh show 10.20.99.1                             # the router's management address: an entry, not FAILED
timeout 3 bash -c 'exec 3<>/dev/tcp/10.20.99.1/443'  # web UI
timeout 3 bash -c 'exec 3<>/dev/tcp/10.20.99.1/22'   # ssh
```

| Symptom | Reading |
|---|---|
| ARP resolves, 443 and 22 both refused | Firewall policy — the anti-lockout rules are gone. This page. |
| Nothing answers, from any segment | Router down, or its LAN port. This page. |
| Same-segment works, cross-segment does not | Zone policy. Still this page if the API is unreachable. |
| Only one segment affected | Switch port or VLAN — see [access switch](/docs/runbook/substrate/recovery/console-recovery/access-switch/) or [troubleshooting](/docs/changes/2026/0001-flat-network-to-vlans/troubleshooting/). |

{{< hint warning >}}
**Ping the router's management address and nothing answers, even when it is healthy.** The zone
policy lets management reach the router itself on 443 and 22 only
([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/)), so ICMP to `10.20.99.1` from
management meets the default deny. ARP shows the router is on the segment; the ports show its
policy. Test the ports and a cross-segment host, not ping.
{{< /hint >}}

---

## 2. Get a console

Mini DisplayPort to the monitor, USB keyboard, and the console menu is on screen.

---

## 3. Restore the configuration

OPNsense keeps a history of previous configurations on the box itself, in `/conf/backup/` —
one entry per change, with a timestamp and a description. Nothing needs to be carried in.

From the console menu, choose **Restore a backup**.

{{< hint info >}}
**Read the menu, do not trust the number.** It is option `13` on current builds, but the
numbering has shifted between releases and the entry you want is named, not numbered.
{{< /hint >}}

Pick the last revision **before** the change that caused the outage. The descriptions carry
what changed, which is usually enough to identify it. When in doubt go further back: a
slightly stale configuration that routes is worth more than a current one that does not.

The router applies it and restarts services. Give it a minute.

---

## 4. Verify

From a host on the management segment:

```bash
timeout 3 bash -c 'exec 3<>/dev/tcp/10.20.99.1/443' && echo "web UI back"
ping -c1 10.20.30.11        # a host on another segment - transit policy
ping -c1 1.1.1.1            # egress
```

And from the console's **Shell**, to read the live ruleset rather than what the GUI believes:

```sh
pfctl -sr | grep -c .       # rules actually loaded
pfctl -sr | grep anti-lock  # the rules that let you back in remotely
```

Do not leave the rack until a cross-segment ping works.

---

## 5. Reconcile — a restore rolls back everything

A restore reverts the **whole** of `config.xml` to that point in time, not only the part that
broke: DHCP reservations, Unbound host overrides and aliases, interface assignments, VLANs,
NAT — every change since that revision, including the good ones.

Inventory is the source of truth, so bring the router back up to declared state:

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/dns.yml          # Unbound records
ansible-playbook playbooks/dhcp.yml         # Kea reservations
```

Read the reporting tasks in the output rather than trusting `changed=0`, and see
[Change Management](/docs/policies/change-management/) first — `--check --diff` will not
preview any of it.

Then take a backup, so the inventory's copy is the router as it now is, and commit it through a pull
request:

```bash
make backup-router
```

{{< hint warning >}}
**`opnsense_firewall` is guarded, but it has no savepoint.** It reports by default and writes
nothing without `-e firewall_apply=true`, refuses a broken discovery, withholds deletions unless
`firewall_delete_unmanaged=true`, protects the operator path, checks the API's `result` rather than
the HTTP status, and verifies reachability afterwards.

OPNsense has no firewall savepoint or automatic rollback: `firewall/filter/savepoint`,
`/cancelRollback` and `/revert` each answer `404 "Endpoint not found"`. Instead, the role records the
configuration revision from before the run and reverts over the API if a path is lost **and the
router still answers**.

**If the control host's own path is what broke, nothing reverts on its own.** No timer will fix
it, and waiting is not a recovery step. That case is this page. The run prints the revision id
before it writes anything — `config-<timestamp>.xml` — and that is what to pick under *Restore a
backup*.
{{< /hint >}}
