---
title: "Tenant Operations"
weight: 2
bookCollapseSection: true
aliases:
  - /docs/runbook/building-recovery/build-tenants/
  - /docs/runbook/substrate/building-recovery/build-tenants/
---

# Tenant Operations

For whoever is **building something on Deevnet** — you know Terraform, you may not know Deevnet,
and you want a device or a service running on the platform without learning how the platform is
built.

A picture to keep in mind: the mobile kit is set up at a [CARPE](https://carpe-tech.org/) meetup, and you want a Pico W or an ESP32
on your bench to send messages to a backend. This section walks from "I have nothing" to that, and
then covers running it afterwards.

---

## What a tenant is

A **tenant** is your own isolated slice of the platform, declared in your own Terraform and created
through the Deevnet API. It gets its own network, its own DNS zone, its own Wi-Fi key for devices,
its own MQTT topic space and its own log partitions. Other tenants cannot reach any of it, and you
cannot reach theirs.

You hold **one credential**: a Deevnet API token. You never touch the hypervisor, the router, the
switch or anyone's vault — you declare resources with the `deevnet/deevnet` provider and the
substrate builds them. Everything you get is rebuilt from your repository and your Terraform state,
so the repository *is* the tenant.

The design behind this is in [Tenant architecture](/docs/architecture/tenant/); you do not need to
read it to use this guide.

---

## The service catalog

| Service | What you get | Status |
|---|---|---|
| [Network & workloads](services/network-and-workloads/) | A private `/24`, an anycast gateway, outbound internet, and Fedora VMs | {{< status-badge "active" "Available" >}} |
| [DNS](services/dns/) | `<tenant>.mobile.deevnet.net` and its reverse zone, written by you | {{< status-badge "active" "Available" >}} |
| [Wi-Fi keys](services/wifi-keys/) | A per-tenant key on the IoT SSID, landing your devices on the IoT network | {{< status-badge "active" "Available" >}} |
| [Devices & MQTT](services/devices-and-mqtt/) | A device registry and TLS MQTT accounts confined to your own topics | {{< status-badge "active" "Available" >}} |
| [Logs](services/logs/) | Your own log partitions: workload logs, and device logs arriving over MQTT | {{< status-badge "active" "Available" >}} |
| [State store](services/state-store/) | An S3 backend for your Terraform state | {{< status-badge "active" "Available" >}} |
| [Secrets, metrics, dashboards, identity, object storage, code delivery](services/coming-soon/) | Designed, not yet built | {{< status-badge "planned" "Coming soon" >}} |

---

## Reading path

1. **Getting started** — [Before you start](getting-started/before-you-start/) →
   [Admission](getting-started/admission/) → [First apply](getting-started/first-apply/)
2. **[Walkthrough: a Pico W or ESP32 talking to a backend](walkthrough-mqtt-device/)** — the whole
   thing end to end, in one Terraform file and two short firmware sketches
3. **Services** — one page per service, when you need the details
4. **Operating** — [Day 2](operating/day-2/) and [Troubleshooting](operating/troubleshooting/)
5. **[Pi Lab](pi-lab/)** — the Raspberry Pi bank, when your project needs a Pi rather than a VM
6. **[Take it home on a Pi](take-it-home/)** — after the meetup: your app and devices on a Pi of
   your own, same topics and tokens, no Deevnet behind it

The operator's side of all this — admitting your name — is
[Tenant Admission](/docs/runbook/substrate/tenant-admission/).
