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
| **Documentation** | [deevnet.github.io/terraform-provider-deevnet](https://deevnet.github.io/terraform-provider-deevnet/) |

---

## Why Terraform for tenants

The substrate is configured by procedural automation; tenants use Terraform. A tenant is created and
destroyed often, so its tooling has to track what it owns, plan a change before making it, and
destroy cleanly. Terraform does all three, and it is what a tenant developer is likely to know
already. The substrate is configured rather than created, and gains nothing from state it would then
have to guard.

---

## Resources

**The provider has its own documentation site, [Deevnet Terraform Provider](https://deevnet.github.io/terraform-provider-deevnet/).** Its
[resource reference](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/) is generated from the provider's schemas, with every
argument and attribute of the seven resources:

| Resource | Declares |
|---|---|
| [`deevnet_tenant`](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/tenant/) | The tenant, by `name` |
| [`deevnet_workload`](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/workload/) | A VM in the tenant's network |
| [`deevnet_dns_record`](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/dns_record/) | A name in the tenant's zone |
| [`deevnet_iot_wifi_key`](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/iot_wifi_key/) | A Wi-Fi key per trust class |
| [`deevnet_iot_device`](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/iot_device/) | A device in the tenant's registry |
| [`deevnet_iot_address`](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/iot_address/) | A fixed address for a registered device |
| [`deevnet_iot_broker_account`](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/iot_broker_account/) | An MQTT account for a device or a workload |

There are no data sources. The state store is used through Terraform's own `backend "s3"`.

---

## Restore instead of recreate

The provider never drops a secret-bearing resource from state because the API has lost it. It marks
it not present, so the next plan is an **update**, and the update sends the tenant's index and
secrets back from state. That is how a tenant comes back, with the same keys, after the API's
registry is lost. `-replace` issues new keys instead. The provider's
[Restore Instead of Recreate](https://deevnet.github.io/terraform-provider-deevnet/docs/guides/restore/) guide covers each resource.

The same rule means a workload whose VM is gone, but which the registry still lists, shows no change
([Deevnet API → How it behaves on repair](/docs/platforms/deevnet-software/deevnet-api/#how-it-behaves-on-repair)).
