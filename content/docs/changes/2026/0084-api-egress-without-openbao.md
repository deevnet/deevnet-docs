---
title: "CHG-0084: The API's Egress List Without OpenBao"
weight: -84
---

# CHG-0084: The API's Egress List Without OpenBao

| | |
|---|---|
| **Date** | 2026-11-23 |
| **Change type** | Upgrade |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-23** |
| **Window** | A few seconds of provisioning while the API restarts, in a work session |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API); read by `dv02hyp002p02`'s egress agent |
| **Automation** | `deevnet.mgmt` `site.yml --tags deevnet-api`, with `deevnet_api_version` v0.28.1 |
| **Risk** | Low. Most likely to go wrong: the new API refuses a request the old one served, found by readiness and the agent's next run |
| **Related changes** | None |
| **Related incidents** | [INC-0007](/docs/incidents/2026/0007-api-sealed-after-power-on/), whose corrective action 1 this is |
| **Related runbooks** | None |

---

## Summary

**The Deevnet API moves from v0.25.0 to v0.28.1, whose `GET /v1/fabric/egress` answers while OpenBao
is sealed** ([INC-0007](/docs/incidents/2026/0007-api-sealed-after-power-on/), action 1). The list is
read from the registry alone and served outside the gate that holds every other `/v1` route until
the API has read OpenBao; the agent's and the operator's tokens are checked against the environment.
v0.26.0 to v0.28.0 changed only the take-home tool, which is not deployed here.

## Goal

- The API reports v0.28.1 and ready.
- With OpenBao sealed and the API restarted, the egress agent's next run reads its list: 200.

## Procedure

### Step 1: Release and stage

`deevnet-provisioning-api` [#85](https://github.com/deevnet/deevnet-provisioning-api/pull/85) and the
release [#86](https://github.com/deevnet/deevnet-provisioning-api/pull/86), tagged `v0.28.1`;
`make stage`.

### Step 2: Deploy, in a work session

The operator opens OpenBao (`make bao-open`): the role stops before writing if it is sealed. Then, in
`deevnet.mgmt`, with `deevnet_api_version` at v0.28.1:

```bash
ansible-playbook playbooks/site.yml --tags deevnet-api
```

**Verify:** `/version` says v0.28.1; `/readyz` is ready; the agent's next run reads 200.

### Step 3: The case that failed

The operator closes the session (`make bao-close`). Then, on `dv02prv001v01`,
`systemctl restart deevnet-api`.

**Verify:** `/readyz` says OpenBao is sealed; the agent's next run reads its list, 200, and its unit
does not fail.

## Undo

Set `deevnet_api_version` back to v0.25.0 and run Step 2 again, in a work session.

## To close

**This change closes when every item below is done.**

- [x] Step 1: v0.28.1 released and staged
- [x] Step 2: deployed; v0.28.1 ready; the agent's run read 200
- [x] Step 3: with OpenBao sealed and the API restarted, the agent's run read 200
- [x] For an Upgrade: `make discover` (`deevnet.mgmt`) run after it, and the Software Catalog updated from its report

## Outcome

**The API runs v0.28.1, and with OpenBao sealed the egress agent reads its list and succeeds.**
All commands ran from the Builder as `a_autoprov`.

| When | Steps | What happened |
|---|---|---|
| 20:26 | | Before: v0.25.0. OpenBao was opened for a work session; the agent's 20:31 run succeeded, as INC-0007 said it would |
| 20:34 | Step 2 | Deployed in 36 s: the image pushed and loaded, a new secret ID for the API's AppRole and the one it replaced destroyed, the container recreated. `/version`: v0.28.1, commit `6f4a149`; `/readyz`: ready, OpenBao ok |
| 20:36 | Step 2 | The agent's run: `GET /v1/fabric/egress` 200, the unit succeeded |
| 22:24 | Step 3 | The work session closed. `/readyz` before the restart: OpenBao sealed. `systemctl restart deevnet-api`; after it, v0.28.1, `/readyz` `{"database":"ok","openbao":"sealed","status":"unavailable"}` |
| 22:26 | Step 3 | The agent's run: `GET /v1/fabric/egress` 200 in the API's log, the unit succeeded (exit 0, not failed). Before v0.28.1 this run answered 503 |

## Follow-ups

None. The rest of INC-0007's work is tracked there: the agent's message for a sealed API (action 2), ADR-0042's wording (3), alerting (4) and the power-on runbook page (5).
