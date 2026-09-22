---
title: "INC-0004: Core Router Stopped Answering During CHG-0018"
weight: 4
---

# INC-0004: Core Router Stopped Answering During CHG-0018

| | |
|---|---|
| **Date** | 2026-09-21 |
| **Site** | mobile |
| **Systems** | `dv02cor002p01` (core router); by consequence, every routed path at the site. Seen from `dv00bld001p01` (the Builder). |
| **Severity** | Site gateway lost: no routing between segments, no site DNS (the router is the resolver), the operator's normal path to the Builder cut. Same-segment traffic on management unaffected. Recovery needs console access to the router. |
| **Status** | Open · {{< inc-status "Investigating" >}} |
| **Times** | EDT (UTC−4) |

---

## Summary

At about 20:14 the core router stopped answering on both its LAN (`10.20.99.1`, `re0`) and its WAN
(`192.168.8.106`, `re1`). This happened in the middle of
[CHG-0018](/docs/changes/2026/0018-central-log-store/): the log store's deploy stalled partway through
pushing a container image to `dv02obs001v01` on Platform, a path that crosses the router. The operator,
working from trusted, lost the Builder and came back in over the travel router's LAN.

**The cause is not established.** Nothing the deploy ran was aimed at the router. The last writes to the
router were the `opnsense_dns` and `opnsense_dhcp` runs at about 19:50, more than 20 minutes earlier. The
router has not yet been examined at its console.

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

Not yet examined: the router itself (console, uptime, logs).

## Root cause

Not established.

## Recovery

*Pending: the operator is at the router's console.*

## Contributing factors

- **No monitoring.** The loss was found by the operator losing their session, about 11 minutes later
  (ADR-0023, Proposed).
- **The router is a single point for everything routed**, including the operator's path to the Builder
  and the site's DNS.

## Corrective actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Establish why the router stopped answering, from its console and persistent logs (the in-memory buffer holds about 50 seconds) | `dv02cor002p01` | {{< action-status "Open" >}} |

## Preventive actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| | *To be decided once the cause is known* | | |

## Follow-ups

| # | Follow-up | Where | Status |
|---|-----------|-------|--------|
| 1 | After recovery, confirm the router's configuration survived: the zone policy (57 rules), Kea reservations and Unbound overrides | `dv02cor002p01` | {{< action-status "Open" >}} |
| 2 | Resume CHG-0018 Step 4 only after follow-up 1; `dv02obs001v01` is left half-deployed | CHG-0018 | {{< action-status "Open" >}} |

## Lessons learned

*To be written once the cause is known.*

## Related changes

- [CHG-0018: The Central Log Store](/docs/changes/2026/0018-central-log-store/): in progress when this
  happened.

## Related runbooks

-
