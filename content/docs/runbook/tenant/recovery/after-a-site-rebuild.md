---
title: "After a Site Rebuild"
weight: 1
---

# After a Site Rebuild

The operator tells you what was rebuilt. What you do depends on which part it was.

| What the site rebuilt | What comes back on its own | What you do |
|---|---|---|
| **The Deevnet API's registry** | Nothing about you, until you apply | `terraform apply`. Your state restores your tenant with the same index and keys, and the plan is otherwise empty. Only if another tenant has taken your index meanwhile are you given a new one, and your network and workloads are rebuilt on it |
| **The tenant hypervisor** | Your network, once the operator reconciles your tenant | Your **workloads do not come back yet**: see below |
| **DNS, the state store, the log store or dashboards** | Your zone and key, your state access, log tokens and dashboards login, once the operator reconciles your tenant | Re-check your names: see below. Log lines and dashboards stored on a lost host are gone |

## Your workloads, after a tenant hypervisor rebuild

A rebuilt tenant hypervisor comes back without your VMs. The site still lists them, so a plain
`terraform apply` shows **no changes** and rebuilds nothing. The API does rebuild a workload's VM,
with the same address and name, whenever that workload is applied again. But there is no tested way
yet to make your apply send it. Until there is, ask the operator. Closing this is on the
[Tenant Platform](/docs/roadmap/infrastructure/mobile/tenant-platform/) roadmap.

Anything a workload kept on its own disk is gone. Your application comes back the way it arrived:
the workload pulls it ([ADR-0017](/docs/architecture/decisions/tenant-model/0017-tenant-code-delivery/)).

## Your names, after a DNS rebuild

A reconcile recreates your zone and your update key, but not the records in it. Your workloads'
names and any `deevnet_dns_record` you declared need to be published again, and a plain apply shows
no change for them either — the same gap as workloads. Check with `dig` against the site resolver,
and ask the operator if names are missing.

## Check

- `terraform plan` is empty.
- Your workloads answer at their addresses, and your names resolve through the site resolver.
- A device can still publish, and its lines reach your logs.
