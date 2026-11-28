---
title: "TLS Cert Automation: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/tls-cert-automation/
  - /projects/tls-cert-automation/
weight: 7
tasks_completed: 15
tasks_in_progress: 1
tasks_planned: 7
---

# TLS Cert Automation: Project Plan

Every certificate the site serves chains to the **Deevnet Root CA**, kept offline with the Mobile
Site CA ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/),
[CHG-0033](/docs/changes/2026/0033-deevnet-pki/)). The Mobile Substrate CA signs every substrate
certificate on the control node, OpenBao's listener included, and `certs.yml` renews them. The
Builder, the hypervisors and every management-plane VM trust the root at the OS level; tenants trust
it as `deevnet-root-ca.pem`. Proxmox, the core router and the Omada controller serve site
certificates, and every client verifies them
([Certificates](/docs/runbook/substrate/certificates/)). The Tenant Device CA is in OpenBao, waiting
for device enrollment.

**Roadmap item:** [TLS Cert Automation](/docs/roadmap/infrastructure/substrate/tls-cert-automation/)

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

- ✅ An offline Deevnet Root CA and Mobile Site CA, made on the `pi-pki` machine ([Root of Trust](/docs/runbook/root-of-trust/)), CHG-0033 {{< added "2026-10-05" >}}
- ✅ The Mobile Substrate CA, its key in the site vault, signing every substrate certificate by Ansible {{< added "2026-10-05" >}}
- ✅ The Mobile Tenant Device CA, its key made outside OpenBao, held in the site vault and imported (CHG-0036) {{< added "2026-10-31" >}}
- ✅ The Site CA name-constrained to Deevnet names and private addresses {{< added "2026-10-05" >}}
- ✅ The ADR-0030 root, bootstrap intermediate and OpenBao intermediate retired; no online key can mint a CA (R-11 closed) {{< added "2026-10-05" >}}
- ✅ Ceremony tooling: transfer manifests and checks (`deevnet-pki-transfer.sh`, `deevnet-pki-sign.sh`), the media tool (`deevnet-pki-media.sh`), the guided ceremony (`deevnet-pki-ceremony.sh`), and the `pi-pki` image {{< added "2026-10-05" >}}

---

## Trust Distribution 🔄

- ✅ The Deevnet Root CA in the OS trust store of the Builder, both hypervisors and every management-plane VM {{< added "2026-10-05" >}}
- ✅ Tenants: `deevnet-root-ca.pem` on the downloads site, embedded in `tenant-check.sh` and `install-provider.sh` {{< added "2026-10-05" >}}
- ✅ Operator computer trust procedure, Windows included {{< added "2026-10-05" >}}
- ✅ The VM templates rebuilt with the Deevnet Root CA, server and tenant flavors {{< added "2026-10-05" >}}
- ✅ The tenant repositories and eds's lightd on `deevnet-root-ca.pem` {{< added "2026-10-05" >}}
- 🔄 Tenant workloads cloned before CHG-0033 trust only the retired root in their OS store, until each is replaced {{< added "2026-10-05" >}}

---

## Substrate Services ✅

- ✅ Every substrate service serves a Substrate CA certificate (API, state store, broker, log store, Grafana, downloads, OpenBao) {{< added "2026-10-05" >}}
- ✅ One `certs.yml` playbook that lays down every certificate and trust anchor {{< added "2026-10-02" >}}
- ✅ Proxmox, the core router and the Omada controller on site certificates {{< added "2026-10-02" >}}
- ✅ Every client verifies: the Deevnet API, Packer, the tenant fabric and Ansible {{< added "2026-10-05" >}}

---

## Device Identity ⏳

- ⏳ Device enrollment through the Deevnet API: the Tenant Device CA signs a device's request ([CHG-0034](/docs/changes/2026/0034-device-certificates/)) {{< added "2026-10-05" >}}
- ⏳ mTLS at the broker: client certificates from the Tenant Device CA, authorized by their URI {{< added "2026-10-03" >}}

---

## Later ⏳

- ⏳ A clean re-root once device identity is built: a new Deevnet Root CA and Site CA, and every issuing CA under them, made in a ceremony that starts with a bootloader reset ([Certificates](/docs/standards/certificates/) 5.10). The first ceremony ran without one {{< added "2026-10-05" >}}
- ⏳ Automatic renewal (ADR-0030 open question 1) {{< added "2026-10-02" >}}
- ⏳ Expiry monitoring, with ADR-0023 {{< added "2026-10-02" >}}
- ⏳ Keeping a twenty-year root readable for twenty years: the root outlives any Pi, USB drive or microSD, and today's tools may not run in 2046. Open: how often to refresh the key media onto new drives, what keeps the ceremony machine buildable, whether a different medium (paper backup, a hardware token) belongs in custody, or whether a shorter root lifetime is simpler {{< added "2026-10-03" >}}
- ⏳ The PowerDNS API and the Builder's artifact server on site certificates {{< added "2026-10-05" >}}
