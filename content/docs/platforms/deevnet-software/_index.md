---
title: "Deevnet Software"
weight: 6
bookCollapseSection: true
---

# Deevnet Software

The provisioning software and runtime tools this site had to build for itself, because nothing off
the shelf draws the [substrate–tenant boundary](/docs/architecture/tenant/boundary/) the way the
architecture needs. Everything else the site runs is third-party, and is listed in the
[Software Catalog](/docs/platforms/software-catalog/). Versions and licenses for these are there
too, under [Deevnet's Own Software](/docs/platforms/software-catalog/#deevnets-own-software).

| Software | What it is | Runs on |
|---|---|---|
| [Deevnet API](deevnet-api/) | The provisioning API: every tenant request goes through it | `dv02prv001v01` |
| [Terraform provider](terraform-provider/) | `deevnet/deevnet`: how a tenant declares itself to the API | Tenant laptops |
| [Log bridge](log-bridge/) | Carries device log lines from the MQTT broker into each tenant's log partition | `dv02msg001v01`, and the Pi backend image |
| [Tenant egress agent](egress-agent/) | Keeps a default route in every tenant VRF on the fabric exit node | `dv02hyp002p02` |
| [deevnet-kit](deevnet-kit/) | The API's stand-in on a Raspberry Pi, for the take-home backend image | The Pi backend image |
| [Image factories](image-factories/) | Build the OS images, the VM templates, and the service images whose binaries can't be redistributed | The Builder |

Three more pieces are in-house but described with what they build: the tenant fabric's Terraform
([Tenant Fabric](/docs/platforms/tenant-compute/tenant-hypervisors/tenant-fabric/)), the Ansible
collections that configure the substrate, and the reference tenant, `deevnet-tenant-tdemo`
([First apply](/docs/runbook/tenant/getting-started/first-apply/)).

Two helper binaries are built from the API's repository and share its tag:
`deevnet-broker-account` on the messaging VM and `deevnet-log-user` on the log store. The API reaches
each over SSH through a forced command, so it never holds a login to either host.
