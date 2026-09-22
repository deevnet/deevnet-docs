---
title: "INC-0004: Core Router Hard-Hung During CHG-0018"
weight: 4
---

# INC-0004: Core Router Hard-Hung During CHG-0018

| | |
|---|---|
| **Date** | 2026-09-21 |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` (core router); by consequence, every routed path at the site. Seen from `dv00bld001p01` (the Builder). |
| **Severity** | Site gateway lost: no routing between segments, no site DNS (the router is the resolver), the operator's normal path to the Builder cut. Same-segment traffic on management unaffected. Recovery needs console access to the router. |
| **Status** | Open · {{< inc-status "Mitigated" >}}. Service restored by a power-cycle at about 20:33, and the configuration was verified intact. The cause is not established. |
| **Times** | EDT (UTC−4) |

---

## Summary

At about 20:14 the core router stopped answering on both its LAN (`10.20.99.1`, `re0`) and its WAN
(`192.168.8.106`, `re1`). This happened in the middle of
[CHG-0018](/docs/changes/2026/0018-central-log-store/): the log store's deploy stalled partway through
pushing a container image to `dv02obs001v01` on Platform, a path that crosses the router. The operator,
working from trusted, lost the Builder and came back in over the travel router's LAN.

At the console the router was **hard-hung**: no video, and the keyboard's lock light did not respond,
so the OS was not servicing USB. A power-cycle brought it back at 20:33:34. Its configuration came back
intact: the firewall shows no drift against inventory, and the Kea reservations and Unbound overrides
match what was there before.

**The cause is not established.** Nothing the deploy ran was aimed at the router. The last write to its
configuration was at 19:50:49, from the `opnsense_dns` and `opnsense_dhcp` runs, 23 minutes before the
hang. No log survives from the minutes before it: the root filesystem was not cleanly dismounted, and
crash dumps are disabled.

## Impact

- No routing between segments from about 20:14. That includes trusted → management, which is the
  operator's normal path to the Builder.
- No site DNS. The router is the resolver for management and for the Builder's `enp4s0`.
- Everything behind the router unreachable from the Builder: Platform (`dv02obs001v01`, OpenBao, the
  API), tenants, IoT Backend.
- CHG-0018's deploy stopped half-done. On `dv02obs001v01`, VictoriaLogs was started and vmauth never
  deployed. The syslog port's firewall rule was never added.
- **Not affected:** hosts on the management L2 segment reached each other directly. The switch, AP,
  both hypervisors, `dv02nms001v01`, `dv02col001v01` and `dv02bld001v01` all answered.

## Detection

The operator lost their session to the Builder and could not get back by the usual path. Claude found
the router down while investigating the operator's report at about 20:25, roughly 11 minutes after it
happened. Nothing alerted, because the site has no monitoring yet (ADR-0023 is Proposed).

## Timeline

| Time | Event |
|---|---|
| ~19:50 | CHG-0018 Step 1: `opnsense_dns` adds `dv02obs001v01` and `dv02col001v01` A records (the delete run was blocked and not made). `opnsense_dhcp` updates 15 reservations in place, a known idempotency defect, and `col`'s on its unchanged MAC. Both succeeded. |
| 19:53 | New VMs built. `vm-identity` audit and rebuild rerun succeed, including OpenBao on Platform through the router. |
| 19:55–20:03 | Builder-collection `site.yml` runs against `dv00bld001p01` and `dv02bld001v01` (CHG-0018 departure). The Builder's `enp4s0` is re-applied and reconnects three times: 19:55:32, 19:57:48, 20:03:33. Each is under a second, and the router answers throughout. |
| ~20:10 | Log-store deploy starts on `dv02obs001v01`. It logs in to OpenBao and issues a certificate (control node → Platform, through the router: succeeds), writes files, and pushes and loads the VictoriaLogs image (about 26 MB, succeeds). Then it starts the VictoriaLogs container. |
| **20:14:20** | The deploy's last line: pushing the vmauth image (about 24 MB) to `dv02obs001v01`. It never completes. This is the latest time the router is known to have been forwarding. |
| 20:16 | The operator connects to the Builder from `192.168.8.170`, the travel router's LAN, instead of from trusted (`10.20.10.100`). |
| 20:22:29 onward | The operator's SSH forward to the router's web UI fails repeatedly: `connect_to 10.20.99.1 port 443: failed`. |
| ~20:25 | The operator reports being knocked out. Claude confirms that `10.20.99.1` does not answer ARP from the Builder, that ports 443, 22 and 53 fail, and that everything else on management answers. |
| 20:26:49 | Re-probe: LAN still down. WAN `192.168.8.106:443` fails too, and its ARP entry is stale. |
| 20:27 | This record opened. The operator goes to the router's console. |
| ~20:31 | At the console: no video output, and the keyboard's lock light does not respond. The router is hard-hung. |
| 20:33:34 | The operator power-cycles it; this is the boot time the router reports. |
| 20:35:35 | Boot completes (`OPNsense 26.7.3_11`). The LAN VLANs are up and the WAN takes `192.168.8.106` by DHCP. |
| 20:35:59 | From the Builder, the router's 443, 22 and 53, Platform (`10.20.25.22:22`) and the trusted gateway all answer. Site DNS resolves. |
| ~20:40 | Configuration verified read-only through the API: `opnsense_firewall` in its default report-only mode finds 57 managed rules against 57 desired, with 0 to add, update or delete. Kea has 15 reservations and Unbound 22 overrides, both unchanged. |

## Symptoms

- From the Builder, `ip neigh` shows `10.20.99.1 dev enp4s0 FAILED`. Ping gives 100% loss with send
  errors, which is ARP failing, not a filter.
- TCP 443, 22 and 53 to `10.20.99.1` fail. DNS: `communications error to 10.20.99.1#53: timed out`.
- Every routed destination fails, for example `10.20.25.22:22` and `10.20.10.1:443`.
- On the same segment, `10.20.99.9`, `.10`, `.21`, `.22`, `.40`, `.41` and `.97` all answer.
- WAN side: `192.168.8.106` (`re1`, MAC `00:e0:4c:29:1e:4f`) was in the Builder's neighbour table as
  STALE, and TCP 443 to it fails. The WAN may not listen on 443 by design, so this only suggests that the
  whole box is down, not just its LAN.

## Investigation

Ruled out, with evidence:
- **The Builder's own network.** `enp4s0` is up with its declared profile. The Builder reaches every
  same-segment host, and its last NetworkManager event was 20:03:33, eleven minutes before the loss.
- **The Claude CLI uninstall task in the `workstation` role.** It is a no-op. The CLI is the native
  install at `~/.local/bin/claude`, and the task reports changed whenever `npm` exits 0.
- **The log-store deploy acting on the router.** Every task it ran is listed in its log, and none
  targets the router. It wrote files on `dv02obs001v01` and started a container there.

**At the console:** no video, and no response from the keyboard's lock light. That is a hard hang,
not a panic that printed and stopped, and not a reboot loop.

**After the power-cycle,** read through the API because SSH is not open to `a_autoprov`:
- `boottime Tue Sep 22 0:33:34 UTC` (20:33:34 EDT), and `config Mon Sep 21 23:50:49 UTC` (19:50:49
  EDT). Nothing changed the configuration after the DNS/DHCP runs.
- The system log the API returns is the current day's file, which in UTC begins at 20:00 EDT. It holds
  **nothing between 20:00 and this boot**, so the 14 minutes before the hang left no trace. The boot log
  says why:
  - `WARNING: / was not properly dismounted` and `mount pending error: blocks 816 files 22`. Unflushed
    writes, which would include the last minutes of logging, were lost at the hard stop.
  - `Configuring crash dump device: /dev/null`. Crash dumps are disabled, so a kernel panic could not
    have been captured either.
- **Two hypotheses. Neither is confirmed, and nothing here rules either out:**
  1. **Thermal or load, on fanless hardware** (raised by the operator). The router is a fanless
     ZimaBoard, and its work has grown. Since CHG-0007 it enforces 57 inter-zone rules, so every packet
     between segments goes through pf. It routes on a stick: management → Platform traffic enters and
     leaves on the same `re0` trunk, so that link carries every image push twice. The evening was its
     heaviest yet: VM builds, image pushes, OpenBao calls, and DNS/DHCP API writes. A fanless board sheds
     heat only through its case, so heat built up over the evening would show in no single command. A
     hard lockup with no video and no keyboard response is consistent with a thermal or power stop.
     **Against, or at least unsettled:** about 50 MB of image pushes is light work for a gigabit router,
     so load alone should not hang a healthy box. If load was the trigger, something was already
     marginal.
  2. **The Realtek NIC driver.** Both NICs are Realtek RTL8168/8111 on FreeBSD's `re(4)` driver, which
     has a reputation for hanging under load. The hang came while an image was crossing `re0`. The first
     push, 26 MB, crossed it without trouble.
- **Read after recovery (20:38):** 44.1 °C on the only sensor exposed, one ACPI thermal zone
  (`hw.acpi.thermal.tz0`), not per-core. Load average 0.50, and 755 MB of 8 GB memory in use. That rules
  out memory pressure. It says nothing about the temperature at 20:14, five minutes after a cold boot.

## Root cause

Not established. The router hard-hung, and the evidence that could say why was not kept. See
Contributing factors.

## Recovery

The operator power-cycled the router at the console at about 20:33. It booted normally, and routing,
DNS and the Platform path were back by 20:35:59. Its configuration was verified read-only (see the
Timeline, ~20:40).

**State left:** CHG-0018 Step 4 is half-done on `dv02obs001v01`. The VictoriaLogs container is running,
vmauth is not deployed, and the syslog firewall rule is not added, so nothing on that host is reachable
off-box except what firewalld allows by default.

## Contributing factors

- **No monitoring.** The loss was found by the operator losing their session, about 11 minutes later
  (ADR-0023, Proposed).
- **The router is a single point for everything routed**, including the operator's path to the Builder
  and the site's DNS.
- **No evidence survives a hard hang.** Crash dumps go to `/dev/null`, and logging is local only. The
  last minutes of logs were lost with the unclean stop. Off-box syslog would have kept them, and that is
  exactly what CHG-0018 Step 6 builds.

## Corrective actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Establish why the router hung. The console and local logs had nothing, so this now depends on catching a recurrence with the preventive actions below in place. | `dv02cor002p01` | {{< action-status "Open" >}} |
| 2 | Test both hypotheses by reproducing deliberately. In a window where losing the router is acceptable, with its console attached, push sustained traffic across VLANs (`iperf3` from a management host to a Platform host, so it crosses `re0` both ways). Record the temperature every few seconds, to somewhere that survives a hang. Then compare with the same test after a cool-down. A hang that tracks temperature points to heat; a hang at low temperature under load points to the driver or the hardware. | `dv02cor002p01` | {{< action-status "Open" >}} |
| 3 | Expose per-core temperatures (load `coretemp`), so a thermal reading means the CPU rather than one ACPI zone | `dv02cor002p01` | {{< action-status "Open" >}} |

## Preventive actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Send the router's syslog off-box so the last lines before a hang survive it | CHG-0018 Step 6 | {{< action-status "Open" >}} |
| 2 | Enable a crash dump device (`dumpdev`) on the router so a kernel panic leaves a dump | `dv02cor002p01` | {{< action-status "Open" >}} |
| 3 | Monitor the router's reachability, so a hang is detected by alert rather than by the operator losing a session | ADR-0023 | {{< action-status "Open" >}} |

## Follow-ups

| # | Follow-up | Where | Status |
|---|-----------|-------|--------|
| 1 | After recovery, confirm the router's configuration survived: the zone policy (57 rules), Kea reservations and Unbound overrides | `dv02cor002p01` | {{< action-status "Done" >}} 2026-09-21 |
| 2 | Resume CHG-0018 Step 4 only after follow-up 1; `dv02obs001v01` is left half-deployed | CHG-0018 | {{< action-status "Open" >}} |

## Lessons learned

*To be written once the cause is known.*

## Related changes

- [CHG-0018: The Central Log Store](/docs/changes/2026/0018-central-log-store/): in progress when this
  happened.

## Related runbooks

-
