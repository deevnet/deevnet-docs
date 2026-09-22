---
title: "INC-0004: Core Router Lost: a Hard Hang, Then Recurring re0 Watchdog Timeouts"
weight: 4
---

# INC-0004: Core Router Lost: a Hard Hang, Then Recurring re0 Watchdog Timeouts

| | |
|---|---|
| **Date** | 2026-09-21 |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` (core router); by consequence, every routed path at the site. Seen from `dv00bld001p01` (the Builder). |
| **Severity** | Site gateway lost: no routing between segments, no site DNS (the router is the resolver), the operator's normal path to the Builder cut. Same-segment traffic on management unaffected. Recovery needs console access to the router. |
| **Status** | Open · {{< inc-status "Investigating" >}}. **It recurs.** After the first hang, `re0` stopped again with the box alive, and the console showed `re0: watchdog timeout`. Timeouts continued overnight and after a cable swap. The router is reachable at the time of writing, but the fault is not fixed. |
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

### It happened again, differently

At about 21:19 the router's LAN stopped answering again, but this time **the box stayed alive**. The
console responded, and `dmesg` showed **`re0: watchdog timeout`**: the LAN NIC had stopped, not the
machine. The management → Platform path then failed intermittently all night, as `nms`'s upload retries
and `obs`'s server logs both record. The operator swapped the cables and rebooted, and still saw four
more watchdog timeouts by the next morning.

The second event **confirms the NIC driver hypothesis for that event**. It does not establish that the
first event, a full hard hang, had the same cause.

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
| 20:44 | CHG-0018's deploy re-run completes across the router, including the vmauth image push that the first event interrupted. |
| 20:50–21:19 | CHG-0018 trials journal shipping from `dv02nms001v01`, a management host, to `obs` on Platform. From 21:19 `nms` begins uploading its whole journal across the router: a backfill of 194,077 lines. |
| **~21:19** | **Second event.** From the Builder, `10.20.99.1` stops answering ARP (`INCOMPLETE`, then `FAILED`), and every routed path fails. The operator reports that the router is up and **its console responds**. |
| ~21:25 | At the console, `dmesg` shows **`re0: watchdog timeout`**. The operator reboots the router, and afterwards still cannot get back in by the normal path. *Exact times were not recorded.* |
| 21:10 → 07:30 | `nms`'s uploader retries whenever it loses the store, and restarts **337 times** overnight. **Every 10-minute window from 21:10 to 07:30 has failures.** They are `Failed to connect` (routing to Platform), `Could not resolve host` (the router is the resolver), and connections dying mid-stream (TLS `unexpected eof`, `Connection reset`, `No route to host`, 300-second timeouts). The longest stretches of DNS failure: 22:50–23:30, 02:50–03:40, 05:10–05:30 and 06:50–07:30. |
| 21:10 → 07:30 | On `obs` in the same period: vmauth has **0 restarts** but logs **68 TLS handshakes that time out part-way**, and VictoriaLogs logs **4 journald streams from `nms` cut off mid-transfer**. That is the path dropping, not a server fault. |
| 2026-09-22, morning | The operator swaps cables and reboots the router, then sees **four further `re0` watchdog timeouts** during the session. The operator's impression is that **the cable swap may have helped**: fewer timeouts. The rate was not measured either side of the swap. |
| 2026-09-22 07:54 | The router answers from the Builder: 443, Platform, and DNS. |
| 2026-09-22 ~07:55 | CHG-0018 is rescoped. `nms`'s journal shipping is stopped and disabled, which removes its traffic across `re0`. **Further timeouts after this cannot be attributed to that upload.** |
| 2026-09-22 08:09 | CHG-0018 completes with no traffic of its own crossing `re0`. |

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
  2. **The Realtek NIC driver.** *Update: confirmed for the second event (`re0: watchdog timeout`), and
     not yet shown for the first.* Both NICs are Realtek RTL8168/8111 on FreeBSD's `re(4)` driver, which
     has a reputation for hanging under load. The hang came while an image was crossing `re0`. The first
     push, 26 MB, crossed it without trouble.
- **Read after recovery (20:38):** 44.1 °C on the only sensor exposed, one ACPI thermal zone
  (`hw.acpi.thermal.tz0`), not per-core. Load average 0.50, and 755 MB of 8 GB memory in use. That rules
  out memory pressure. It says nothing about the temperature at 20:14, five minutes after a cold boot.

## Root cause

**For the second event and the recurrences, the immediate fault is established:** the core router's
LAN NIC, `re0` (Realtek RTL8168/8111 on FreeBSD's `re(4)` driver), hits **watchdog timeouts**. Each one
stops the interface that carries every VLAN. That is every routed path at the site, and the resolver.
A cable swap did not stop them.

**Why `re0` times out is not established:** the driver, the chip, the cabling, heat, or load. The cable
swap may have reduced the timeouts, in the operator's impression, but it did not stop them. **Whether the first
event, a hard hang with no video and no keyboard, was the same fault is also not established.** A NIC
watchdog timeout does not by itself stop the console, so the first event may have been a different
failure, or a worse form of the same one. No evidence from it survived (see Contributing factors).

## Recovery

The operator power-cycled the router at the console at about 20:33. It booted normally, and routing,
DNS and the Platform path were back by 20:35:59. Its configuration was verified read-only (see the
Timeline, ~20:40).

**First event:** CHG-0018 Step 4 was left half-done on `dv02obs001v01`. It was completed at 20:44 and
verified.

**Second event and after:** the router was rebooted by the operator, then rebooted again after a cable
swap. It is reachable at 07:54 on 2026-09-22, but watchdog timeouts continue, so service is **not**
considered restored. CHG-0018 was narrowed so that it adds no traffic across `re0`: nothing ships to
the store, and the router's syslog is excluded until the NIC is stable.

## Contributing factors

- **No monitoring.** The loss was found by the operator losing their session, about 11 minutes later
  (ADR-0023, Proposed).
- **The router is a single point for everything routed**, including the operator's path to the Builder
  and the site's DNS.
- **No evidence survives a hard hang.** Crash dumps go to `/dev/null`, and logging is local only. The
  last minutes of logs were lost with the unclean stop. Off-box syslog would have kept them. CHG-0018
  built the store, but the router's syslog is deliberately not sent there until the NIC is stable,
  because the NIC is the path.
- **The shipping trial added traffic across `re0` during the second event**: `nms`'s full-journal
  backfill of 194,077 lines, and its overnight retries. It did not start the fault; the first event
  predates it. It may have made the fault more frequent. It was stopped on 2026-09-22.

## Corrective actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Establish why the router hung. The console and local logs had nothing, so this now depends on catching a recurrence with the preventive actions below in place. | `dv02cor002p01` | {{< action-status "Open" >}} |
| 2 | Test both hypotheses by reproducing deliberately. In a window where losing the router is acceptable, with its console attached, push sustained traffic across VLANs (`iperf3` from a management host to a Platform host, so it crosses `re0` both ways). Record the temperature every few seconds, to somewhere that survives a hang. Then compare with the same test after a cool-down. A hang that tracks temperature points to heat; a hang at low temperature under load points to the driver or the hardware. | `dv02cor002p01` | {{< action-status "Open" >}} |
| 3 | Expose per-core temperatures (load `coretemp`), so a thermal reading means the CPU rather than one ACPI zone | `dv02cor002p01` | {{< action-status "Open" >}} |
| 4 | Fix or replace the `re0` path. **First, Realtek's vendor driver in place of the in-tree `re(4)`** (Follow-up 3), which OPNsense ships for exactly this symptom. If timeouts persist after that, **replace the router with hardware whose NICs are not Realtek, and that has more than two ports**, so the trunk isn't the only LAN link (the operator's preference). Disabling hardware offloads on `re0` is a further candidate, unverified. | `dv02cor002p01` | {{< action-status "Open" >}} |
| 5 | Capture the next watchdog timeout with context: the timestamp, `netstat -I re0` counters before and after, and the temperature. This comes from the console until off-box syslog is safe to enable. | `dv02cor002p01` | {{< action-status "Open" >}} |

## Preventive actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Send the router's syslog off-box so the last lines before a hang survive it. **Declined** by the operator on 2026-09-22: the central store is for tenants only ([ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/)), and no separate router log path is wanted. Evidence of the next hang is to come from the console and from crash dumps (Preventive action 2). | — | {{< action-status "Declined" >}} |
| 2 | Enable a crash dump device (`dumpdev`) on the router so a kernel panic leaves a dump. **Now the main way the next event leaves evidence**, since off-box syslog was declined, so do it before or with the vendor-driver change. | `dv02cor002p01` | {{< action-status "Open" >}} |
| 3 | Monitor the router's reachability, so a hang is detected by alert rather than by the operator losing a session | ADR-0023 | {{< action-status "Open" >}} |

## Follow-ups

| # | Follow-up | Where | Status |
|---|-----------|-------|--------|
| 1 | After recovery, confirm the router's configuration survived: the zone policy (57 rules), Kea reservations and Unbound overrides | `dv02cor002p01` | {{< action-status "Done" >}} 2026-09-21 |
| 2 | Resume CHG-0018 Step 4 only after follow-up 1; `dv02obs001v01` is left half-deployed | CHG-0018 | {{< action-status "Done" >}} 2026-09-21 |
| 3 | **Move the router from the in-tree `re(4)` driver to Realtek's vendor driver**, as its own change record, because it changes a kernel module on the site gateway and needs a reboot. Details below the table. | new CHG | {{< action-status "Open" >}} |
| 4 | Only once `re0` is stable, send the router's syslog to the central store. **Declined** on 2026-09-22 with Preventive action 1 (ADR-0027: tenants only). | — | {{< action-status "Declined" >}} |

**Follow-up 3, the vendor driver, from OPNsense's own plugin source** (`opnsense/plugins`,
`net/realtek-re`, read 2026-09-22):
- `PLUGIN_NAME= realtek-re`, `PLUGIN_COMMENT= Realtek re(4) vendor driver`,
  `PLUGIN_DEPENDS= realtek-re-kmod`.
- Its description: *"This is the official driver from Realtek and can be loaded instead of the FreeBSD
  driver built into the GENERIC kernel if you experience issues with it (eg. watchdog timeouts), or your
  card is not supported."* and *"Please note this driver requires a system reboot to activate."*
- It works by a loader drop-in: `if_re_load="YES"`, `if_re_name="/boot/modules/if_re.ko"`.

**Inference, to confirm in the change record:**
- OPNsense packages plugins with an `os-` prefix, so it installs as `os-realtek-re`.
- Removing the plugin removes that loader file, and the in-tree driver returns at the next reboot.
  That would be the rollback.

The change needs:
- console access, because a driver that fails to attach takes the LAN down
- the timeout rate measured before and after, so the result is a measurement, not an impression

## Lessons learned

*To be written once the cause is known.*

## Related changes

- [CHG-0018: The Central Log Store](/docs/changes/2026/0018-central-log-store/): in progress when this
  happened.

## Related runbooks

-
