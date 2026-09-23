---
title: "Network & Workloads"
weight: 1
---

# Network & Workloads {{< status-badge "active" "Available" >}}

## What you get

Creating the tenant gives you a network before you declare anything else:

| | |
|---|---|
| A `/24` of your own | from `10.20.128.0/18` — `deevnet_tenant.this.subnet` |
| An anycast gateway | `.1` of it — `deevnet_tenant.this.gateway` |
| Outbound internet | SNAT on the way out; the outside world sees the platform, not your subnet |
| Isolation | your network is its own routing domain (a VRF). Other tenants cannot reach it, and it cannot reach them |

A **workload** is a Fedora VM on that network, addressed by cloud-init from your subnet (`.10`
upward; `.2`–`.9` are reserved). There is no DHCP on tenant networks — addresses are assigned, not
leased, so a rebuilt workload comes back at the same address.

## Declare one

```hcl
resource "deevnet_workload" "backend" {
  tenant    = deevnet_tenant.this.name
  name      = "backend"          # lowercase letters, digits and dashes, up to 20
  cores     = 2                  # default 2
  memory_mb = 2048               # default 2048
  # disk_gb = 32                 # can grow, never shrink
}

output "backend" {
  value = { address = deevnet_workload.backend.address, fqdn = deevnet_workload.backend.fqdn }
}
```

The workload gets a name in your zone automatically — `deevnet_workload.backend.fqdn`.

**You do not need a workload.** A device-only tenant — say a sensor that publishes to MQTT and a
backend that lives elsewhere — declares no VM at all. A VM nothing runs on costs memory on a small
hypervisor and proves nothing.

## Getting onto it

SSH reaches workloads from the **management and trusted networks only**
([ADR-0018](/docs/architecture/decisions/0018-operator-access-to-tenants/)); the guest and IoT
networks cannot reach them, by design.

{{< hint warning >}}
**`ssh_keys` does not work yet.** The resource accepts it, but the API sends the keys to Proxmox
URL-encoded with spaces as `+`, which Proxmox rejects. Until that is fixed, workloads carry only the
platform's automation key, so **getting your code onto a workload goes through the operator** —
see [code delivery](/docs/runbook/tenant/services/coming-soon/#code-delivery-to-workloads) for where
this is heading.
{{< /hint >}}

## What it does not do

- **No inbound from outside.** Nothing on the internet can reach a workload
- **No devices on your network.** Devices join the IoT Wi-Fi, not your tenant network; the two meet
  at the [MQTT broker](/docs/runbook/tenant/services/devices-and-mqtt/), which both dial out to
- **No backup.** A workload is rebuilt from your code, not restored. Data you care about belongs
  somewhere you declared
