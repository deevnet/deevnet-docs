---
title: "SSL Cert Automation"
weight: 5
tasks_completed: 14
tasks_in_progress: 2
tasks_planned: 3
---

# SSL Cert Automation

The site's root CA is kept offline in the inventory vault, and OpenBao issues from an intermediate
under it ([ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/),
[CHG-0031](/docs/changes/2026/0031-site-root-ca/)). Ansible issues one-year certificates to the
Deevnet API, the state store, the broker, the log store's proxy, Grafana and tenant downloads as it
builds each one, and `certs.yml` renews them. The Builder, the hypervisors, every management-plane VM
and the VM template trust the root at the OS level; tenants trust it as `deevnet-mobile-root-ca.pem`.
Proxmox and the Omada controller serve site certificates, and their clients verify them; the core
router's is imported and waits on one manual GUI step
([CHG-0032](/docs/changes/2026/0032-appliance-certificates/),
[Certificates](/docs/runbook/substrate/certificates/)).

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

A new build or a repave comes up with the right certificates and the right trust on every substrate
host and tool, with no browser warning and no client skipping verification.

**In Scope**
- The site's certificate hierarchy and its custody
- Trust distribution: substrate hosts, the Builder, the VM template, the operator's computer, tenants
- Site certificates for every substrate service and appliance interface
- Renewal and expiry monitoring

**Out of Scope**
- Public-facing certificates
- Client certificate authentication
- Code signing certificates

---

## Certificate Authority ✅

- ✅ Internal CA in OpenBao, issuing to Platform services (ADR-0016, CHG-0010)
- ✅ CA delivered to tenants with their credentials (downloads, admission fingerprint)
- ✅ Offline root in ansible-vault, OpenBao intermediate under it (ADR-0030 §1–§2)
- ✅ Bootstrap intermediate in ansible-vault for the core router and hypervisors (ADR-0030 §3)
- ✅ Re-root tenants and scripts onto the offline root, once
- ✅ Root file renamed `deevnet-mobile-root-ca.pem`; applications read the CA from a variable

---

## Trust Distribution ✅

- ✅ Root in the OS trust store of every substrate host and domain VM
- ✅ Root in the Builder's trust store
- ✅ Root baked into the VM template
- ✅ Operator computer trust procedure

---

## Substrate Services 🔄

- ✅ Platform services serve TLS from the site CA (API, state store, broker, log store, Grafana, downloads)
- ✅ One `certs.yml` playbook that lays down every certificate and trust anchor
- ✅ Proxmox admin UI
- 🔄 Core router admin UI and API (certificate imported; the GUI selection is the manual step)
- ✅ Omada controller UI and API
- 🔄 Clients stop skipping verification (Deevnet API, Packer, tenant fabric, Ansible): Proxmox and Omada done, the core router waits on its GUI step

---

## Later ⏳

- ⏳ Automatic renewal (ADR-0030 open question 1)
- ⏳ Expiry monitoring, with ADR-0023
- ⏳ OpenBao listener, PowerDNS API and the Builder's artifact server on site certificates
