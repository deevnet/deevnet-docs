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

**Reach your workloads by name, never by address.** A workload's name always follows it. Its address
comes from your tenant's index, and a tenant that is re-created after a full site rebuild without its
state may get a different index, and so different addresses. Anything you pinned to an address
breaks then; anything that uses the name doesn't.

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

You log in with your own key
([ADR-0028](/docs/architecture/decisions/tenant-model/0028-tenant-workload-login/)):

- **`ssh_keys`** takes the **public** keys that may log in. The private key never leaves your
  computer, and the substrate holds nothing to log in with.
- **The account is `tenant`,** reported as `login_user`, with passwordless sudo. Log in with
  `ssh tenant@<fqdn>` from `DVNTM-TD`.
- **Nobody else has a key.** A workload carries no substrate account; the operator gets in only if
  you add the operator's key to `ssh_keys`.
- **Keys are written when the workload is built.** To change them, change `ssh_keys` and
  `terraform apply -replace=deevnet_workload.<name>`; a workload boots straight to ready.
- **Updates are yours.** A workload is built from an up-to-date template and does not upgrade itself;
  `sudo dnf upgrade` when you choose.

SSH reaches workloads from `DVNTM-TD`, and from the site's management and trusted networks. The
guest and IoT networks cannot reach them, by design.

[Deploy Your App to a Workload](/docs/runbook/tenant/deploy-your-app/) takes it from there: your
container, your `kit.env`, and a systemd unit.

## What it does not do

- **No inbound from outside.** Nothing on the internet can reach a workload
- **No devices on your network.** Devices join the IoT Wi-Fi, not your tenant network; the two meet
  at the [MQTT broker](/docs/runbook/tenant/services/devices-and-mqtt/), which both dial out to
- **No backup.** A workload is rebuilt from your code, not restored. Data you care about belongs
  somewhere you declared
