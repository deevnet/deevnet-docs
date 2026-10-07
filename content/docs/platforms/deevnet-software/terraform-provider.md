---
title: "Terraform Provider"
weight: 2
---

# Terraform Provider

`deevnet/deevnet`: how a tenant declares itself to the [Deevnet API](/docs/platforms/deevnet-software/deevnet-api/).
It is the tenant side of the [substrate–tenant boundary](/docs/architecture/tenant/boundary/).

| | |
|---|---|
| **Repository** | `terraform-provider-deevnet`, Go, terraform-plugin-framework ([version](/docs/platforms/software-catalog/#deevnets-own-software)) |
| **Runs on** | Tenant laptops and the Builder. It is not in the public registry |
| **Distributed by** | `make release-build`: zips for macOS and Linux on amd64 and arm64, with `SHA256SUMS`, `install-provider.sh` and `tenant-check.sh`. `make stage` puts them on [tenant downloads](/docs/runbook/tenant/getting-started/before-you-start/#getting-the-provider) |
| **Configuration** | `DEEVNET_API_ENDPOINT`, `DEEVNET_API_TOKEN`, `DEEVNET_API_CACERT` |

---

## Why Terraform for tenants

The substrate is configured by procedural automation; tenants use Terraform. A tenant is created and
destroyed often, so its tooling has to track what it owns, plan a change before making it, and
destroy cleanly. Terraform does all three, and it is what a tenant developer is likely to know
already. The substrate is configured rather than created, and gains nothing from state it would then
have to guard.

---

## Resources

| Resource | Declares | Gives back |
|---|---|---|
| `deevnet_tenant` | The tenant, by `name` | Its index and network, DNS zone and TSIG key, state-store credentials, log endpoint and tokens, dashboards login, and its API token |
| `deevnet_workload` | A VM: `cores`, `memory_mb`, `disk_gb`, `ssh_keys` | Its VMID, MAC, address and name |
| `deevnet_dns_record` | A name for an address in the tenant's subnet, or one reserved for its device | Its FQDN |
| `deevnet_iot_wifi_key` | A Wi-Fi key per trust class | The SSID, VLAN and key |
| `deevnet_iot_device` | A device, by MAC and trust class | Its registry entry |
| `deevnet_iot_address` | A fixed address for a registered device | The address, and the device's name in the tenant's zone |
| `deevnet_iot_broker_account` | An MQTT account for a device, with publish and subscribe patterns | What was granted, and the password |

There are no data sources. The state store is used through Terraform's own `backend "s3"`.

---

## Restore instead of recreate

The provider never drops a secret-bearing resource from state because the API has lost it. It marks
it not present, so the next plan is an **update**, and the update sends the tenant's index and
secrets back from state. That is how a tenant comes back, with the same keys, after the API's
registry is lost. `-replace` issues new keys instead.

The same rule means a workload whose VM is gone, but which the registry still lists, shows no change
([Deevnet API → How it behaves on repair](/docs/platforms/deevnet-software/deevnet-api/#how-it-behaves-on-repair)).
