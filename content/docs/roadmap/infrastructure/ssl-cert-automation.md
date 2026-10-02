---
title: "SSL Cert Automation"
weight: 5
tasks_completed: 3
tasks_in_progress: 0
tasks_planned: 14
---

# SSL Cert Automation

The site's certificate authority is OpenBao's `pki/` mount (ADR-0016). Ansible issues site-CA
certificates to the Deevnet API, the state store, the broker, the log store's proxy, Grafana and tenant
downloads as it builds each one, and tenants trust the CA as `site-ca.pem`.
[ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/) (Proposed) sets the
next version: an offline root with an OpenBao intermediate, trust in every OS trust store, and site
certificates on Proxmox, the core router and the Omada controller, all laid down by the build.

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

## Certificate Authority 🔄

- ✅ Internal CA in OpenBao, issuing to Platform services (ADR-0016, CHG-0010)
- ✅ CA delivered to tenants with their credentials (downloads, admission fingerprint)
- ⏳ Offline root in ansible-vault, OpenBao intermediate under it (ADR-0030 §1–§2)
- ⏳ Re-root tenants, scripts and device firmware onto the offline root, once

---

## Trust Distribution ⏳

- ⏳ Root in the OS trust store of every substrate host and domain VM
- ⏳ Root in the Builder's trust store
- ⏳ Root baked into the VM template
- ⏳ Operator computer trust procedure

---

## Substrate Services 🔄

- ✅ Platform services serve TLS from the site CA (API, state store, broker, log store, Grafana, downloads)
- ⏳ One `certs.yml` playbook that lays down every certificate and trust anchor
- ⏳ Proxmox admin UI
- ⏳ Core router admin UI and API
- ⏳ Omada controller UI and API
- ⏳ Clients stop skipping verification (Deevnet API, Packer, tenant fabric, Ansible)

---

## Later ⏳

- ⏳ Automatic renewal (ADR-0030 open question 1)
- ⏳ Expiry monitoring, with ADR-0023
- ⏳ OpenBao listener, PowerDNS API and the Builder's artifact server on site certificates
