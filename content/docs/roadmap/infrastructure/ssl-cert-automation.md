---
title: "SSL Cert Automation"
weight: 5
tasks_completed: 16
tasks_in_progress: 2
tasks_planned: 8
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

## Deevnet PKI (ADR-0031) ⏳

The design that replaces the chain CHG-0031 and CHG-0032 built, which stays in service until this is
done: an offline Deevnet Root CA and Site CAs, a Substrate CA issued by Ansible, and a Tenant Device
CA for mTLS ([Trust and Identity](/docs/architecture/trust-and-identity/)).

- ✅ Ceremony transfer tooling: hash manifests, private-key refusal, request and chain checks (`deevnet-pki-transfer`, `deevnet-pki-sign`)
- ✅ Ceremony image for a Raspberry Pi 4 (`pi-pki`): no radios or network services, no SSH or automation account, read-only root, tools baked in
- ✅ Ceremony media prepared on the Pi (`deevnet-pki-media`): key media as encrypted drives, transfer media as plain FAT32
- ⏳ The operator's ceremony: Deevnet Root CA and the Mobile Site CA ([Root of Trust](/docs/runbook/root-of-trust/)), [CHG-0033](/docs/changes/2026/0033-deevnet-pki/)
- ⏳ The Mobile Substrate CA in the site vault; every substrate certificate from it, by Ansible, OpenBao's listener included
- ⏳ Re-root every host, image, tenant and computer to the Deevnet Root CA; retire the OpenBao and bootstrap intermediates
- ⏳ The Mobile Tenant Device CA in OpenBao; device enrollment through the Deevnet API
- ⏳ mTLS at the broker: client certificates from the Tenant Device CA, authorized by their URI

---

## Later ⏳

- ⏳ Automatic renewal (ADR-0030 open question 1)
- ⏳ Expiry monitoring, with ADR-0023
- ⏳ Keeping a twenty-year root readable for twenty years: the root outlives any Pi, USB drive or microSD, and today's tools may not run in 2046. Open: how often to refresh the key media onto new drives, what keeps the ceremony machine buildable, whether a different medium (paper backup, a hardware token) belongs in custody, or whether a shorter root lifetime is simpler
- ⏳ OpenBao listener, PowerDNS API and the Builder's artifact server on site certificates
