---
title: "First Apply"
weight: 3
aliases:
  - /docs/runbook/building-recovery/verify-tenants/
  - /docs/runbook/substrate/building-recovery/verify-tenants/
---

# First Apply

## Lay out a repository

A tenant is code in its own repository
([ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/)). Two layouts work:

- **A tenant repository of its own**, like the reference tenant
  [`deevnet-tenant-tdemo`](https://github.com/deevnet/deevnet-tenant-tdemo) — copy it and change the
  name
- **Inside your application's repository**, at `infra/deevnet-tenant-<name>/`, beside the firmware.
  EdS and Ma Bell do this, so the device and the infrastructure it depends on change together

Either way:

```
deevnet-tenant-<name>/
├── main.tf
├── site-ca.pem        # from the operator; gitignored is fine, it is not secret
├── .gitignore         # *.tfstate*, .terraform/
└── Makefile           # optional; tdemo's sets the endpoint and CA for you
```

## The minimum: one resource

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    deevnet = { source = "deevnet/deevnet", version = "~> 0.3" }
  }
}

# Reads DEEVNET_API_ENDPOINT, DEEVNET_API_TOKEN, DEEVNET_API_CACERT
provider "deevnet" {}

resource "deevnet_tenant" "this" {
  name = "bench1"            # exactly the name you were admitted with
}

output "api_token" {
  value     = deevnet_tenant.this.api_token
  sensitive = true
}
```

Everything else — workloads, names, Wi-Fi keys, devices, broker accounts — hangs off
`deevnet_tenant.this.name` and is added to this same configuration later.

## Apply

```bash
export DEEVNET_API_ENDPOINT=https://api.mobile.deevnet.net:8080
export DEEVNET_API_CACERT=$PWD/site-ca.pem
export DEEVNET_API_TOKEN=<the enrollment token>

terraform init
terraform plan
terraform apply
```

The apply **spends the enrollment token**, the API allocates your tenant an index, and the
substrate builds your network, DNS zone, state-store access and log partitions. It takes under a
minute.

## Switch to your own token

From now on the credential is your tenant's own token, which your state holds:

```bash
export DEEVNET_API_TOKEN=$(terraform output -raw api_token)
```

Put that line in whatever you use to set up a shell for this project. If a later command says
`No API token`, this is the line that is missing.

{{< hint warning >}}
**Your Terraform state now holds every credential the tenant was issued**, and for most of them it
is the only copy ([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/) §4).
Never commit it. Losing it means asking the operator to restore what the API can, and re-issuing the
rest — which for a device means reflashing it. Once the tenant matters, move the state into the
[state store](/docs/runbook/tenant/services/state-store/).
{{< /hint >}}

## Check it worked

```bash
terraform plan -detailed-exitcode     # exit 0: your declaration and the substrate agree
terraform state show deevnet_tenant.this | grep -E 'index|subnet|gateway|dns_zone'
```

You should see an index, a `/24` inside `10.20.128.0/18`, its `.1` as the gateway, and
`<name>.mobile.deevnet.net` as your zone. That is a tenant. Next:
[the walkthrough](/docs/runbook/tenant/walkthrough-mqtt-device/) puts a device on it.

Checks worth running once you have a workload and names:

| Check | How | Expected |
|---|---|---|
| Names | `dig <record>.<name>.mobile.deevnet.net +short` from `DVNTM-TD` | your address |
| Gateway and egress | from your workload: `ping <gateway>`, `curl -sI https://fedoraproject.org` | both answer |
| Logs | write a line with your ingest token and read it back with your read token ([Logs](/docs/runbook/tenant/services/logs/)) | the line comes back |
