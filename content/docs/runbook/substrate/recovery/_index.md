---
title: "Recovery"
weight: 7
bookCollapseSection: true
aliases:
  - /docs/runbook/recovery/
---

# Recovery

Getting service back when something has failed.

- [Console Recovery](console-recovery/) — getting back into a device when the network cannot reach it: core router, hypervisors, access switch and AP
- [Omada Controller Recovery](omada-controller-recovery/) — restoring the network controller from a data snapshot, including falling back from a bad upgrade
- [Rebuild the Core Router](rebuild-core-router/) — a fresh OPNsense install, brought back from a saved configuration or from nothing
- [Rebuild a Hypervisor](rebuild-hypervisor/) — a fresh Proxmox install, and what each hypervisor runs back on top of it
- [Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/) — reinstalling the hardware Builder from a temporary builder VM, while it is still there to help
- [Build the Builder](/docs/runbook/substrate/building-recovery/build-the-builder/) — making the Builder from a bare machine, when it is already gone

## What a failure takes with it

**When one component fails, this is what is rebuilt, what has to be redone after it, and who feels
it.** It describes the site as it works today; where something doesn't come back on its own, the
last column says so. The order of a full build is in
[Building Infrastructure](/docs/runbook/substrate/building-recovery/#greenfield-build-sequence).

| Failed | Rebuild | Then redo | Tenants feel | Doesn't come back on its own |
|---|---|---|---|---|
| **Builder** | [Build the Builder](/docs/runbook/substrate/building-recovery/build-the-builder/), or [Repave the Builder](/docs/runbook/substrate/building-recovery/repave-builder/) if it is still there | Stage artifacts; rebuild locally built images from source | Nothing directly | The router's configuration copies and the cold-fallback controller's snapshot |
| **Core router** | [Rebuild the Core Router](rebuild-core-router/) | Redeploy the Deevnet API and reconcile, which rewrites tenants' DNS forwards | Tenant name resolution, until then | — |
| **Identity VM** (OpenBao, tenant DNS) | The VM; OpenBao and PowerDNS from their roles | If OpenBao's storage was lost: lock in its new initialization, restart the API, reconcile; tenants' next apply resupplies their secrets ([INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/)). Template and fabric builds need `PVE_CREDS_SOURCE=inventory` until OpenBao is back | Names, until republished | Tenants' DNS records: a reconcile restores zones and keys, not records. The Tenant Device CA's key, if storage was lost |
| **Provisioning VM** (Deevnet API, registry, state store) | The VM, the API and the store | Tenants are admitted again; a tenant that still has its state restores from it, one that doesn't starts again | All tenants, until they are back | The registry, the audit log and tenants' state: there is no copy. A tenant that starts again gets new device secrets, and its devices need re-provisioning |
| **Messaging VM** (broker, log bridge) | The VM, VerneMQ and the bridge | Redeploy the API, which pins the broker's host key | Device MQTT | Tenants' broker accounts |
| **Observability VM** (logs, Grafana, downloads) | The VM and its roles | Reconcile, which restores log users and Grafana organizations; publish the downloads again | Logs and dashboards, until then | Stored logs |
| **Omada controller** | The VM, then the manual setup | Adopt the AP again ([Omada Controller Recovery](omada-controller-recovery/)) | Device Wi-Fi | Tenants' Wi-Fi keys: no tested path puts them back |
| **Management hypervisor** | [Rebuild a Hypervisor](rebuild-hypervisor/), then every VM on it | Every row above except the Builder and the core router | All tenants | Everything in those rows |
| **Tenant hypervisor** | [Rebuild a Hypervisor](rebuild-hypervisor/), the fabric and egress | Reconcile each tenant, which restores its networks; tenants push their applications again | Their workloads | Tenants' workloads: a plain apply sees no change ([After a Site Rebuild](/docs/runbook/tenant/recovery/after-a-site-rebuild/)) |

**A cell in the last column is a place where the site can't yet rebuild something from code.** The
[2026-10 Rebuild and Access review](/docs/architecture/reviews/2026-10-rebuild-and-access/) tracks
each one.

---

Rebuilding a site or a host from nothing is covered by [Building Infrastructure](/docs/runbook/substrate/building-recovery/). What happened in past failures is under [Incident Records](/docs/incidents/).
