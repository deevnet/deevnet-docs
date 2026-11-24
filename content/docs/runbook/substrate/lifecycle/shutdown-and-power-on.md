---
title: "Shutdown and Power-On"
weight: 5
---

# Shutdown and Power-On

How the Mobile Factory is powered down and brought back. **One playbook shuts the substrate down
in dependency order. Bringing it back needs no playbook: once each machine is powered on, its
services and service VMs start on their own.** After power-on the site runs, and tenants have their services and egress, but
the Deevnet API serves no tenant work until a work session opens OpenBao.

A routine shutdown and power-on needs no change record. If either goes wrong, open an
[incident record](/docs/runbook/substrate/incident-management/incident-record-template/).

## Shutting down

**`shutdown.yml` stops everything in order, verifying each stage is down before the next begins.**
From `ansible-collection-deevnet.mgmt` on the Builder:

```bash
ansible-playbook playbooks/shutdown.yml -e confirm_shutdown=yes
```

Without `confirm_shutdown=yes` it stops at its first task and changes nothing.

| Stage | What | How |
|---|---|---|
| 1 | Every running VM on both hypervisors | Through the Proxmox API, in reverse of each VM's start order, each given its own shutdown timeout (`mgmt_vm.startup` in inventory) and stopped if it does not finish in time |
| 2 | Both hypervisors | Powered off, and waited for until they stop answering |
| 3 | The Pi lab | The same |
| 4 | The core router, `dv02cor002p01` | Halted through its API. After this nothing is reachable over the network |
| 5 | The Builder, `dv00bld001p01` | Powered off locally |

**The access switch, the AP and the edge router stay on.** The switch carries the traffic the earlier
stages need, the AP has its own PoE injector, and the edge router is the way back in.

Shutting down ends any work session: OpenBao comes back sealed.

## Powering on

**Power on the core router first, then the hypervisors and the Builder.** The hypervisors start
their service VMs themselves, in each VM's start order. Tenant DNS on `dv02idn001v01` is first, and
OpenBao starts beside it, sealed. The Deevnet API on `dv02prv001v01` starts, finds OpenBao sealed, and
waits for it ([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/)
§2).

**After power-on, with OpenBao sealed:**

| Service | State |
|---|---|
| Tenants' workloads, devices, broker, log store and dashboards | Running. None of them reads OpenBao |
| The exit node's egress agent (`dv02hyp002p02`) | Reads the tenant list and keeps each tenant's default route. Since API v0.28.1 that list is served while OpenBao is sealed |
| The Deevnet API | `/healthz` 200. `/readyz` 503, `"openbao":"sealed"`. Every other `/v1` route answers 503 until a work session |
| Provisioning (tenant creation, certificates, enrollment, the API's own deployment) | Waits for a work session |

### Checking it came back

**`make discover` (`ansible-collection-deevnet.mgmt`) reads every system and says which did not
answer.** Then, on each hypervisor, `qm list` shows every service VM running, and
`systemctl --failed` lists nothing. On the exit node, `deevnet-egress-agent.service` must not be
among them.

The egress agent's log says what the API answered. A 503 (the API up, not ready) leaves the unit
succeeded; a refused token, any other answer, or no answer fails it. A failed agent keeps the
routes it last wrote, so tenants keep their egress while it is put right.

The update watcher's daily run, missed while the Builder was off, runs once soon after it starts.

### Opening a work session

**Tenant work needs OpenBao open.** When there is tenant work to do, from
`ansible-collection-deevnet.mgmt`:

```bash
ANSIBLE_ASK_VAULT_PASS=true make bao-open
```

and `make bao-close` at the end. [A work session](/docs/runbook/substrate/building-recovery/openbao-keys/#a-work-session)
describes both. With the session open the API's `/readyz` answers 200.
