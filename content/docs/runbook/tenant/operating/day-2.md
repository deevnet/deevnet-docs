---
title: "Day 2"
weight: 1
---

# Day 2

Running a tenant after the first apply. Everything here happens in your own repository, with your
own token; none of it needs the operator unless it says so.

---

## Your token

Every session starts with:

```bash
export DEEVNET_API_ENDPOINT=https://api.mobile.deevnet.net:8080
export DEEVNET_API_CACERT=$PWD/site-ca.pem
export DEEVNET_API_TOKEN=$(terraform output -raw api_token)
```

The token lives in your state and nowhere else. If the state is gone, so is the token — see
[Losing things](#losing-things).

## Checking for drift

```bash
terraform plan -detailed-exitcode
```

Exit `0` means your declaration and the platform agree. Exit `2` means something differs — usually
because the platform lost an object and the provider wants to restore it (below), occasionally
because you changed code and forgot to apply.

## Upgrading the provider

The provider is pinned by your `required_providers` constraint (`~> 0.4`), and `init` locks the
exact version. A new provider version only takes effect after:

```bash
terraform init -upgrade
```

**Check the version before relying on a new service.** A tenant only receives what its provider
knows how to read — a tenant created on 0.2.x never saw its log tokens until it upgraded and was
reconciled.

## Rotating a credential

| Credential | Rotate with | Cost |
|---|---|---|
| Wi-Fi key | `terraform apply -replace=deevnet_iot_wifi_key.devices` | every device reflashed |
| Broker account | `terraform apply -replace=deevnet_iot_broker_account.<name>` | that device (or workload) reconfigured |
| API token, TSIG, state, log tokens | ask the operator | — |

## When the platform loses something

If the platform loses an object you declared — a backend rebuilt, a record gone — the provider
does not quietly create a new one with new credentials. It marks it `present = false`, and the next
apply **restores** it with the index, addresses and secrets your state already holds:

```bash
terraform plan      # shows the restore
terraform apply
```

This is why your state matters: it is the copy the platform restores *from*.

## Losing things

| You lost | What happens |
|---|---|
| Your state, but have a backup | restore the file (or re-point the backend) and carry on |
| Your state, no backup | ask the operator. The API can hand back what it holds; what it only ever held as a hash (broker passwords) or never returned again (Wi-Fi keys) is re-issued — so devices are reflashed |
| The enrollment token before first apply | ask for a new admission |

Keeping state in the [state store](/docs/runbook/tenant/services/state-store/) and a copy of it
somewhere you trust is the cheap insurance.

## Tearing down

```bash
terraform destroy
```

Removes your workloads, network, DNS zone, Wi-Fi key, device registry entries and broker accounts,
and revokes your tokens. It does **not** remove:

- **logs already written** — they age out with retention
- **keys already flashed into devices** — they stop authenticating, but they are still on the
  device

Destroy and recreate therefore issues **new** device credentials: the same name, a new key, and a
reflash. Re-applying the same code otherwise rebuilds the tenant identically, and it is worth doing
once on purpose rather than finding out when you need it.
