---
title: "INC-0007: The API Answered 503 for a Day After the Site Powered On"
weight: -7
---

# INC-0007: The API Answered 503 for a Day After the Site Powered On

| | |
|---|---|
| **Date** | 2026-11-22 |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API), `dv02idn001v01` (OpenBao), `dv02hyp002p02` (the exit node and its `deevnet-egress-agent`) |
| **Severity** | Low in effect. From the site's power-on at 20:25 on 2026-11-22, every `/v1` request to the API answered 503, and the exit node's egress agent failed every five minutes. No tenant lost its egress: the agent left its routes as they were, and the exit node's own reboot restored them from disk. No tenant work was asked for |
| **Status** | Open · {{< inc-status "Hardening" >}}. The cause is fixed: since API v0.28.1 ([CHG-0084](/docs/changes/2026/0084-api-egress-without-openbao/), 2026-11-23) the egress list answers while OpenBao is sealed. Actions 2, 3 and 5 are done; action 4, alerting, is open |
| **Times** | EST (UTC−5) |

---

## Summary

**After the site was shut down and powered on again, the Deevnet API started while OpenBao was
sealed, as [ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/)
intends, and so answered 503 to every `/v1` request until an operator opens a work session.** That
includes the one request something running makes: the exit node's egress agent reading the list of
tenant VRFs. That route needs nothing from OpenBao, but the API builds the service behind every `/v1`
route only once it has read OpenBao, and gates all of `/v1` on it.

The agent did what it was built to: kept the tenant routes it had, and tried again. The exit node,
rebooted by the same power cycle, brought the routes back from the file the agent last wrote. So
nothing broke, but for a day the agent reported "cannot reach" every five minutes, a failed unit that
looks the same as a real outage, and a rebuilt exit node in that state would have had no routes to
give its tenants.

## Impact

- **Tenants:** none found. All four tenant VRFs on `dv02hyp002p02` held their default route, and
  `vrf_tdemo` and `vrf_eds` reached `1.1.1.1` on 2026-11-23.
- **Provisioning:** unavailable from 20:25 on 2026-11-22, as it is outside any work session. None was
  asked for.
- **Signal:** `deevnet-egress-agent.service` on the exit node failed 761 times from 2026-11-20 to
  2026-11-23, every five minutes while the API was down or sealed, each logged as "cannot reach".

## Detection

**Found by chance**, at 19:46 on 2026-11-23, while verifying
[CHG-0083](/docs/changes/2026/0083-patch-pilot/) on `dv02hyp002p02`: `systemctl --failed` listed
`deevnet-egress-agent.service`. Nothing alerts on the API or on the agent (INC-0006's preventive
action 4).

## Timeline

| When | What happened |
|---|---|
| 2026-11-22 10:50:23 | The agent's last successful read: `GET /v1/fabric/egress` 200 |
| 10:53:58–10:59 | The site is shut down in order: `a_autoprov` shuts down the service VMs on `dv02hyp001p01` one by one (VMID 208 at 10:54:13, then 207, 206, 205 and on). The API stops at 10:54:40. `dv02hyp002p02` is down at 10:59:14 and `dv02hyp001p01` at 10:59:19 |
| 10:55–20:24 | The site is off. Whenever the exit node is on, the agent cannot reach the API |
| 20:23:30–20:24:59 | Power-on: `dv02hyp001p01` at 20:23:30, `dv02hyp002p02` at 20:24:11, `dv02prv001v01` at 20:24:59. The VMs start on their own; OpenBao starts sealed |
| 20:25:09 | The API starts, finds OpenBao sealed, and waits for it (ADR-0042 §2). `/readyz` answers `{"openbao":"sealed"}`; every `/v1` request answers 503 |
| 20:25 onward | The agent fails every five minutes: "cannot reach https://api.mobile.deevnet.net:8080; leaving /etc/frr/frr.conf.local as it is". The exit node's routes come from that file, last written 2026-11-14 |
| 2026-11-23 19:46 | Found during CHG-0083 |
| 19:50–20:15 | Investigated (below). Tenant egress verified |

## Symptoms

- `deevnet-egress-agent.service` failed on `dv02hyp002p02`, every run, with `curl: (22) The requested
  URL returned error: 503`.
- `GET /readyz` on the API: `{"database":"ok","openbao":"sealed","status":"unavailable"}`, 503.
  `GET /healthz`: 200.

## Investigation

1. **The API was up.** `/healthz` answered `ok`; `/v1/fabric/egress` without a token answered 401.
   So the 503 came after authentication, from the API's own gate.
2. **The gate is OpenBao's.** In `deevnet-provisioning-api`, `internal/server/server.go`, every `/v1`
   route sits behind `requireSecrets`, which answers 503 until the API has read its backend
   credentials from OpenBao; `cmd/deevnet-api/main.go` builds the tenant service, and with it every
   tenant route, only after that read. `/readyz` said OpenBao was sealed.
3. **The egress route needs no secret.** `GET /v1/fabric/egress` lists the ready tenants from the
   database (`tenant.Service.Egress`) and admits the operator or the agent, whose token comes from
   the environment (`DEEVNET_AGENT_TOKEN`). It is behind the gate only because everything under `/v1`
   is.
4. **The 503s began at a power-on, the agent's failures earlier.** `dv02prv001v01`'s boot history and
   the API's journal: the last 200 at 10:50:23, a guest shutdown at 10:54:40, the next boot at 20:24:59.
   `dv02hyp001p01`'s journal shows the ordered shutdown of the service VMs from 10:54:13.
5. **The routes survived.** `/etc/frr/frr.conf.local` on the exit node, dated 2026-11-14, holds four
   default routes; after its 20:24 boot each tenant VRF had its default route, and two tested reached
   the internet.

## Root cause

**The API gates every `/v1` route on having read OpenBao, so after any start while OpenBao is sealed,
which under ADR-0042 is every start outside a work session, the egress agent cannot read the list it
needs, though that list needs no secret.** ADR-0042 says that "a sealed OpenBao stops provisioning and
nothing else" and that "nothing that runs needs it". The egress agent runs, and through this gate it
does.

## Recovery

None needed for tenants. The agent recovered at the next work session (`make bao-open`, 20:31 on
2026-11-23). Since [CHG-0084](/docs/changes/2026/0084-api-egress-without-openbao/) it does not depend
on one: with OpenBao sealed and the API restarted, its 22:26 run read its list, 200.

## Contributing factors

- **The agent reports a sealed API as an unreachable one.** Its one message, "cannot reach", covers a
  network failure, an API that is down, and an API that is up and waiting for OpenBao, and its unit
  fails the same way for each.
- **The pattern was seen and taken as normal.** [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/)
  recorded, two days earlier, that the API "was already answering 503" with OpenBao sealed, and that
  the agent kept its routes. That was true, and it hid this.
- **Nothing alerts** on the API or the agent, so a failed unit on the exit node was found only by
  looking.

## Corrective actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 1 | Serve `GET /v1/fabric/egress` without waiting for OpenBao: read the registry directly and admit the agent's token, outside the secrets gate. A release, then a change to deploy it | `deevnet-provisioning-api` | {{< action-status "Done" >}} v0.28.1 ([#85](https://github.com/deevnet/deevnet-provisioning-api/pull/85)), deployed by [CHG-0084](/docs/changes/2026/0084-api-egress-without-openbao/), 2026-11-23 |

## Preventive actions

| # | Action | Where | Status |
|---|--------|-------|--------|
| 2 | The egress agent says what the API answered: a 503 is "the API is up and waiting for OpenBao", not "cannot reach", and is not a failed unit; an unreachable API still is | `deevnet.net` `tenant_egress_agent` | {{< action-status "Done" >}} [#55](https://github.com/deevnet/ansible-collection-deevnet.net/pull/55), deployed by [CHG-0085](/docs/changes/2026/0085-egress-agent-says-what-api-answered/), 2026-11-24 |
| 3 | ADR-0042's consequences name what runs that reads the API (the egress agent), and say that after action 1 none of it waits for OpenBao | ADR-0042 | {{< action-status "Done" >}} ADR-0042's Consequences, 2026-11-24 |
| 4 | Alert when the API stops answering, or the agent stops succeeding: INC-0006's action 4 | observability | {{< action-status "Open" >}} |

## Follow-ups

| # | Follow-up | Where | Status |
|---|-----------|-------|--------|
| 5 | A runbook page for shutting the site down (`deevnet.mgmt`'s `shutdown.yml`) and powering it on, saying that after power-on the API serves no `/v1` until a work session opens OpenBao | the runbook | {{< action-status "Done" >}} [Shutdown and Power-On](/docs/runbook/substrate/lifecycle/shutdown-and-power-on/), 2026-11-24 |

## Lessons learned

- **A behavior written down as normal in one incident can be the next one's cause.** "Already
  answering 503" was accurate in INC-0006; the question it left was why something running depended on
  a sealed store at all.
- **A fail-safe that never complains looks like health.** The agent's design kept tenants online, and
  its log said the same thing for every kind of failure, so a day of it read as noise.

## Related changes

- [CHG-0083](/docs/changes/2026/0083-patch-pilot/), during whose verification this was found
- [CHG-0084](/docs/changes/2026/0084-api-egress-without-openbao/), which deployed corrective action 1
- [CHG-0085](/docs/changes/2026/0085-egress-agent-says-what-api-answered/), which deployed preventive action 2
- [CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/), which made OpenBao sealed outside work sessions

## Related incidents

- [INC-0006](/docs/incidents/2026/0006-api-vm-scsi-panic/), the same symptom with a different cause, and the alerting action this one shares
