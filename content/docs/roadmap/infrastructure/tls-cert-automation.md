---
title: "TLS Cert Automation"
aliases:
  - /docs/roadmap/infrastructure/ssl-cert-automation/
weight: 5
tasks_completed: 13
tasks_in_progress: 1
tasks_planned: 6
---

# TLS Cert Automation

Every certificate the site serves chains to the **Deevnet Root CA**, kept offline with the Mobile
Site CA ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/),
[CHG-0033](/docs/changes/2026/0033-deevnet-pki/)). The Mobile Substrate CA signs every substrate
certificate on the control node, OpenBao's listener included, and `certs.yml` renews them. The
Builder, the hypervisors and every management-plane VM trust the root at the OS level; tenants trust
it as `deevnet-root-ca.pem`. Proxmox, the core router and the Omada controller serve site
certificates, and every client verifies them
([Certificates](/docs/runbook/substrate/certificates/)). The Tenant Device CA is in OpenBao, waiting
for device enrollment.

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
- Tenant device identity: client certificates from the Tenant Device CA (ADR-0031 §6)

**Out of Scope**
- Public-facing certificates
- Code signing certificates

---

## Certificate Authority ✅

- ✅ An offline Deevnet Root CA and Mobile Site CA, made on the `pi-pki` machine ([Root of Trust](/docs/runbook/root-of-trust/)), CHG-0033
- ✅ The Mobile Substrate CA, its key in the site vault, signing every substrate certificate by Ansible
- ✅ The Mobile Tenant Device CA, its key inside OpenBao
- ✅ The Site CA name-constrained to Deevnet names and private addresses
- ✅ The ADR-0030 root, bootstrap intermediate and OpenBao intermediate retired; no online key can mint a CA (R-11 closed)
- ✅ Ceremony tooling: transfer manifests and checks (`deevnet-pki-transfer.sh`, `deevnet-pki-sign.sh`), the media tool (`deevnet-pki-media.sh`), the guided ceremony (`deevnet-pki-ceremony.sh`), and the `pi-pki` image

---

## Trust Distribution 🔄

- ✅ The Deevnet Root CA in the OS trust store of the Builder, both hypervisors and every management-plane VM
- ✅ Tenants: `deevnet-root-ca.pem` on the downloads site, embedded in `tenant-check.sh` and `install-provider.sh`
- ✅ Operator computer trust procedure, Windows included
- 🔄 The VM templates rebuilt with the Deevnet Root CA; tenant workloads cloned before CHG-0033 trust only the retired root in their OS store

---

## Substrate Services ✅

- ✅ Every substrate service serves a Substrate CA certificate (API, state store, broker, log store, Grafana, downloads, OpenBao)
- ✅ One `certs.yml` playbook that lays down every certificate and trust anchor
- ✅ Proxmox, the core router and the Omada controller on site certificates
- ✅ Every client verifies: the Deevnet API, Packer, the tenant fabric and Ansible

---

## Device Identity ⏳

- ⏳ Device enrollment through the Deevnet API: the Tenant Device CA signs a device's request (CHG-0034)
- ⏳ mTLS at the broker: client certificates from the Tenant Device CA, authorized by their URI

---

## Later ⏳

- ⏳ Automatic renewal (ADR-0030 open question 1)
- ⏳ Expiry monitoring, with ADR-0023
- ⏳ Keeping a twenty-year root readable for twenty years: the root outlives any Pi, USB drive or microSD, and today's tools may not run in 2046. Open: how often to refresh the key media onto new drives, what keeps the ceremony machine buildable, whether a different medium (paper backup, a hardware token) belongs in custody, or whether a shorter root lifetime is simpler
- ⏳ The PowerDNS API and the Builder's artifact server on site certificates
