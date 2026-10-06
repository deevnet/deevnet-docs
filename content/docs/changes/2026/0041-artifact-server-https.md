---
title: "CHG-0041: The Artifact Server Over HTTPS"
weight: -41
---

# CHG-0041: The Artifact Server Over HTTPS

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Configuration |
| **Classification** | Routine |
| **Status** | Planned |
| **Window** | Unscheduled. A template build and a network-boot install prove it |
| **Site** | mobile |
| **Systems** | `dv00bld001p01` (the artifact server), the kickstarts and templates, the hypervisor bootstrap |
| **Automation** | `deevnet.builder` `artifacts` and `substrate_cert` roles; `deevnet-image-factory` kickstarts and Packer templates |
| **Risk** | Low. Most likely to go wrong: a fetch moved to HTTPS before the machine doing it trusts the Deevnet Root CA |
| **Related changes** | [CHG-0033](/docs/changes/2026/0033-deevnet-pki/) |
| **Related incidents** | None |
| **Related runbooks** | [Stage Artifacts](/docs/runbook/substrate/building-recovery/online-preparation/), [Build a Hypervisor](/docs/runbook/substrate/building-recovery/build-hypervisor/) |

---

## Summary

The artifact server serves everything over plain HTTP, including the automation key that new hosts
trust and a script the hypervisor bootstrap runs as root. With the Deevnet PKI in place it can serve
HTTPS. Plain HTTP stays only where nothing can verify yet: the boot payload that firmware and GRUB
fetch ([2026-10 review: A3](/docs/architecture/reviews/2026-10-rebuild-and-access/#a3-bootstrap-over-plain-http)).

## Goal

- The artifact server answers HTTPS with a Substrate CA certificate.
- Everything after install fetches over HTTPS, verified: Ansible, the control node, installed hosts.
- The kickstart carries the Deevnet Root CA's certificate: `%post` writes it into the trust store,
  and its later fetches (the automation key among them) use HTTPS.
- The hypervisor bootstrap checks what it downloads against a hash published in the runbook.
- Plain HTTP serves only the network-boot payload.

## Scope

**In scope:** the artifact server's TLS, the kickstarts, the templates, the hypervisor bootstrap,
Ansible's fetches.
**Out of scope:** UEFI HTTP boot with an enrolled certificate; the first network-boot hop stays
unverified on the management segment.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| An install fails to fetch over HTTPS | kickstart | The Root CA goes into the trust store before any HTTPS fetch; tested with a template build and a network-boot install |
| The bootstrap hash drifts from the script | the runbook | The role publishes the hash beside the script, and the runbook shows how to read it |

## Prerequisites

- [ ] Vault decrypted (the Substrate CA key, for the certificate)

## Procedure

### Step 1: HTTPS on the artifact server

A Substrate CA certificate from `substrate_cert`, and nginx listening on HTTPS beside HTTP.

**Verify:** `curl --cacert deevnet-root-ca.pem -I https://artifacts.mobile.deevnet.net/` answers `200`.

### Step 2: Installs trust the root first

The kickstarts and templates write the Root CA into the trust store in `%post`, then fetch over HTTPS.

**Verify:** a template build and a network-boot install complete, fetching the key over HTTPS.

### Step 3: The hypervisor bootstrap by hash

The runbook's bootstrap downloads the script, checks its hash, then runs it.

**Verify:** a tampered copy is refused.

### Step 4: Narrow plain HTTP

Plain HTTP serves the network-boot paths only.

**Verify:** a key or script path over HTTP answers `404` or a redirect; a network boot still works.

## Verification

A fresh template build and a network-boot install complete with plain HTTP limited to the boot payload.

## Undo

Re-enable plain HTTP for every path; the HTTPS listener can stay.

## To discover

- Which CA issues the Builder's certificate: it belongs to no site (site code `00`), which is
  [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/)'s open question 1.
- Whether anything else on the site fetches from the artifact server by HTTP and needs moving.
