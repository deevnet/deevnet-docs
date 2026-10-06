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
| **The whole site** | Nothing about you | Wait for the operator's new handover file: it carries a new developer Wi-Fi key. Then apply. With your state, your tenant comes back with its keys. Without it, use the handover's enrollment token and create your tenant again from your repository; it may get a new index, which doesn't matter if you use names, and your devices need new secrets. Then push your application to each workload |
| **DNS, the state store, the log store or dashboards** | Your zone and key, your state access, log tokens and dashboards login, once the operator reconciles your tenant | Re-check your names: see below. Log lines and dashboards stored on a lost host are gone |

## Your workloads, after a tenant hypervisor rebuild

A rebuilt tenant hypervisor comes back without your VMs. The site still lists them, so a plain
`terraform apply` shows **no changes** and rebuilds nothing. The API does rebuild a workload's VM,
with the same address and name, whenever that workload is applied again. But there is no tested way
yet to make your apply send it. Until there is, ask the operator. Closing this is on the
[Tenant Platform](/docs/roadmap/infrastructure/mobile/tenant-platform/) roadmap.

Anything a workload kept on its own disk is gone. Your application comes back the way it arrived:
you push it again ([Deploy Your App to a Workload](/docs/runbook/tenant/deploy-your-app/)). Keep the
steps in a script in your repository, and that is one command.

## Your names, after a DNS rebuild

A reconcile recreates your zone and your update key, but not the records in it. Your workloads'
names and any `deevnet_dns_record` you declared need to be published again, and a plain apply shows
no change for them either — the same gap as workloads. Check with `dig` against the site resolver,
and ask the operator if names are missing.

## Check

- `terraform plan` is empty.
- Your workloads answer at their addresses, and your names resolve through the site resolver.
- A device can still publish, and its lines reach your logs.
