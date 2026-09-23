---
title: "DNS"
weight: 2
---

# DNS {{< status-badge "active" "Available" >}}

## What you get

Your own zone, `<name>.mobile.deevnet.net`, and its reverse zone, served authoritatively by the
platform and delegated from the site resolver — so anything that resolves through the site
(workloads, trusted seats) finds your names. **You write the records; the platform never writes one
on your behalf** ([ADR-0004](/docs/architecture/decisions/0004-tenant-dns-publication/)).

## Declare a record

```hcl
resource "deevnet_dns_record" "api" {
  tenant  = deevnet_tenant.this.name
  name    = "api"                              # -> api.<name>.mobile.deevnet.net
  address = deevnet_workload.backend.address   # must be inside your own subnet
}
```

The matching PTR record is created for you. Workloads already get a name of their own; a record is
for the *service* name you want other things to use, so the workload behind it can change.

## Or write it yourself

The zone also takes **RFC 2136 dynamic updates** signed with your TSIG key, for anything that wants
to publish names at runtime. The details are attributes of your tenant:

| | |
|---|---|
| Server | `deevnet_tenant.this.dns_update_server` (`tdns.mobile.deevnet.net`) |
| Zones | `dns_zone`, `dns_reverse_zone` |
| Key | `tsig_key_name` (your tenant name), `tsig_algorithm` (`hmac-sha256`), `tsig_secret` |

Updates are accepted only from the platform's own networks (management, trusted, and tenant
transit — which is where your workloads' traffic comes from).

## What it does not do

- **Your zone only.** An update signed with your key for anyone else's zone is `REFUSED` by the
  server; it is enforced, not a convention
- **No public DNS.** These names resolve inside the site, not on the internet
- **Devices get no names.** The IoT network is not in your zone; devices find the broker by *its*
  name, and nothing needs to find a device
