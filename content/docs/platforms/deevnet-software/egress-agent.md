---
title: "Tenant Egress Agent"
weight: 4
---

# Tenant Egress Agent

Keeps a default route inside every tenant VRF on the fabric exit node, so each tenant's internet
traffic leaves through the perimeter ([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §7).
Proxmox does not model that route, and the alternative was to give the API root on a hypervisor.
Instead the node pulls the tenant list and renders the route itself.

| | |
|---|---|
| **Source** | `ansible-collection-deevnet.net`, role `tenant_egress_agent`: a Bash script with embedded Python |
| **Runs on** | `dv02hyp002p02`: `/usr/local/sbin/deevnet-egress-agent`, run by `deevnet-egress-agent.timer` two minutes after boot and every five minutes after that |
| **Deployed by** | `ansible-playbook playbooks/tenant-egress-agent.yml` |
| **Reads** | `GET /v1/fabric/egress` from the API, with a token that can read that route and nothing else |
| **Writes** | `/etc/frr/frr.conf.local`. Only when it changes: `pvesh set /cluster/sdn` and a reload of FRR |

A failed fetch leaves the file as it is, so an API outage withdraws no route. A deleted tenant loses
its route on the next run.
