---
title: "CHG-0085: The Egress Agent Says What the API Answered"
weight: -85
---

# CHG-0085: The Egress Agent Says What the API Answered

| | |
|---|---|
| **Date** | 2026-11-24 |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | **Complete, 2026-11-24** |
| **Window** | No outage. A few minutes, operator at the Builder |
| **Site** | mobile |
| **Systems** | `dv02hyp002p02` (the exit node's `deevnet-egress-agent`) |
| **Automation** | `deevnet.net` `playbooks/tenant-egress-agent.yml -e target=dv02hyp002p02` |
| **Risk** | Low. Most likely to go wrong: the new agent misreads a good answer and stops rewriting the tenants' routes, found by its first run and the role's readback of each VRF's default route |
| **Related changes** | [CHG-0084](/docs/changes/2026/0084-api-egress-without-openbao/), which fixed the API side of the same incident |
| **Related incidents** | [INC-0007](/docs/incidents/2026/0007-api-sealed-after-power-on/), whose preventive action 2 this is |
| **Related runbooks** | None |

---

## Summary

**The exit node's egress agent now logs what the Deevnet API answered, and fails its unit only for a
fault, not for an API that is up and not ready**
([INC-0007](/docs/incidents/2026/0007-api-sealed-after-power-on/), action 2). It used to log
"cannot reach" for every failure and fail its unit each time, so a day of an API waiting for
OpenBao looked like an outage. The agent still leaves the tenants' routes as they are whenever it
gets no list.

| The API | The agent logs | The unit |
|---|---|---|
| answers 200 | nothing, or `rewrote` when the list changed | succeeds |
| answers 503 (up, not ready) | `the API is up but not ready (503: <its reason>)` | succeeds, `ExecMainStatus=75` |
| refuses the token (401, 403) | `the API refused this agent's token` | fails |
| answers anything else | `the API answered <status>` | fails |
| gives no answer | `cannot reach <url>` | fails |

`deevnet.net` [#55](https://github.com/deevnet/ansible-collection-deevnet.net/pull/55).

## Goal

- The agent's next run reads its list and succeeds, every tenant VRF keeping its default route.
- A refused token is reported as one, and leaves the route file as it is.

## Procedure

### Step 1: Deploy

**Run** (in `ansible-collection-deevnet.net`, after a `--check --diff` showing only the agent and its
unit change):

```bash
ansible-playbook playbooks/tenant-egress-agent.yml -e target=dv02hyp002p02
```

**Verify:** the role's own run of the agent succeeds and its readback lists a default route in every
tenant VRF; `/etc/frr/frr.conf.local` is not rewritten, the list being unchanged.

### Step 2: A refused token

On the exit node, run the agent once by hand with its environment, a wrong token, and a route file
that does not exist.

**Verify:** it logs `the API refused this agent's token (401)`, exits 1, and writes no file.

## Undo

Revert #55 and run Step 1 again.

## To close

**This change closes when every item below is done.**

- [x] Step 1: deployed; the agent's run succeeded; every tenant VRF has its default route
- [x] Step 2: a refused token reported as one, nothing written
- [x] The timer's next run succeeded on its own

## Outcome

**The agent runs the new script, and its runs read the list and succeed.** All commands ran from the
Builder as `a_autoprov`.

| When | Steps | What happened |
|---|---|---|
| 04:19 | Step 1 | `--check --diff`: only the agent and its unit would change |
| 04:20 | Step 1 | Deployed in 6 s: the agent and its unit changed, nothing else. The role's run of the agent: exit 0, unit succeeded. Readback: `vrf_cdeever`, `vrf_eds`, `vrf_mabell` and `vrf_tdemo` each with a default route via the transit gateway. `frr.conf.local` untouched (still 2026-11-14) |
| 04:21 | Step 2 | A wrong token: `the API refused this agent's token (401); leaving /root/egress-test.conf as it is`, exit 1, no file written |
| 04:25 | | The timer's run on its own: exit 0, unit succeeded |

The 503 path was tested before the merge against a stand-in API, not on the site: making the real
API answer 503 would mean taking its database away.

## Follow-ups

None.
