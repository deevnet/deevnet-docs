---
title: "CHG-0047: Server Certificates for Tenants' Services"
weight: -47
---

# CHG-0047: Server Certificates for Tenants' Services

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. Step 3 waits on an Issuing CA ceremony |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao: a new PKI mount and CA), `dv02prv001v01` (the Deevnet API); the provider; one tenant's workload (`eds`) |
| **Automation** | `deevnet.mgmt` `playbooks/tenant-service-ca.yml`, `site.yml --tags openbao,deevnet-api`; `deevnet-provisioning-api`; `terraform-provider-deevnet`; inventory `mobile` |
| **Risk** | Medium. Most likely to go wrong: the signing role admits a name it should not, which would let a certificate be issued for a substrate name that every client would accept |
| **Related changes** | [CHG-0033](/docs/changes/2026/0033-deevnet-pki/) (built the hierarchy and the Tenant Device CA this follows), [CHG-0034](/docs/changes/2026/0034-device-certificates/) (device certificates, planned and independent of this), [CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/) (where OpenBao's CA keys are kept, planned) |
| **Related incidents** | None |
| **Related runbooks** | [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/), [Certificates](/docs/runbook/substrate/certificates/) |

---

## Summary

A tenant workload cannot serve HTTPS that the site trusts: the Substrate CA certifies only the
substrate, and the Tenant Device CA only devices. The `eds` tenant serves a console over plain HTTP
for that reason.

[ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/) decides a third
issuing CA, the Tenant Service CA, in OpenBao. After this change a tenant sends a signing request
through the Deevnet API for a name in its own zone and receives a one-year server certificate that
chains to the Deevnet Root CA. The `eds` console is the first to use one.

## Goal

- OpenBao has a mount `pki-tenant-service` whose CA is the Mobile Tenant Service CA, chaining to the
  Deevnet Root CA through the Mobile Site CA.
- The mount has one signing role. It signs a request for `console.eds.mobile.deevnet.net`, and
  **refuses** one for `grafana.mobile.deevnet.net`, for `mobile.deevnet.net`, for a wildcard and for
  a name outside `deevnet.net`.
- The API's OpenBao policy allows signing on that role and nothing else on the mount.
- A tenant's `deevnet_certificate` applies and returns a leaf that meets the
  [Certificates standard](/docs/standards/certificates/): the subject, names, usages and lifetime of
  a tenant service certificate, whatever the signing request asked for.
- One tenant cannot obtain a certificate for a name in another tenant's zone.
- `https://console.eds.mobile.deevnet.net/` opens in a browser that trusts only the Deevnet Root CA.
- The Tenant Device CA, its mount and every existing certificate are unchanged.

## Scope

**In scope:** the mount, the CA and its ceremony, the signing role and the API's policy; the API's
certificate route and the provider's resource; the API's release and deployment; one tenant service
moved to HTTPS.

**Out of scope:** revocation; renewal by anything but a tenant's own apply; expiry alerting; device
certificates (CHG-0034); where OpenBao's CA keys are kept (CHG-0036); the tenant runbook and the
architecture pages, which are written when this is built.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The signing role admits a substrate name | every client that trusts the root | The role permits only names at least two labels below the site's zone, and the API builds names only inside the caller's zone. Step 4 asks OpenBao directly for names it must refuse, before the API is given the policy |
| The role copies something from a request | every certificate it signs | The role ignores the request's subject and names. Step 4 signs a request that asks for a CA, a client usage and another name, and reads what comes back |
| The policy change breaks the API's existing access | tenant admission, restore | The policy gains one path; the rest is unchanged. Step 5 reads a tenant after the change |
| The OpenBao role's run disturbs the Tenant Device CA | device certificates, when built | The Tenant Device CA is in state 3 (installed) and its tasks do nothing there. Step 2 reads its certificate before and after |
| The ceremony signs the wrong request | the site's trust | The transfer tooling checks the subject, key size and manifest on each side, and the operator confirms the CA's name and the hashes on paper |
| A tenant's certificate expires unnoticed | that tenant's service | Recorded as a consequence of ADR-0037. Nothing in this change watches it |
| The API is restarted for the new version | tenants applying at that moment | The API is provisioning-only; nothing at runtime depends on it |

## Prerequisites

- [ ] Pull requests merged: `deevnet-docs` (ADR-0037, this record, the standard), `deevnet.mgmt`,
  the inventory
- [ ] The inventory's vaults re-encrypted and its working branch closed
- [ ] Vault decrypted, collections built
- [ ] The ceremony kit to hand: the offline Pi, the `pi-pki` media, the key media, the transfer
  media and the paper record
- [ ] `deevnet-provisioning-api` and `terraform-provider-deevnet` released with the certificate
  route and resource

## Procedure

### Step 1: Read what is there

Read-only.

**Run:**

```bash
curl -s --cacert pki/deevnet-root-ca.pem https://<openbao>:8200/v1/pki-tenant-device/ca/pem | openssl x509 -noout -subject -fingerprint -sha256
curl -s -o /dev/null -w '%{http_code}\n' --cacert pki/deevnet-root-ca.pem https://<openbao>:8200/v1/pki-tenant-service/ca/pem
```

**Verify:**

1. The Tenant Device CA is the certificate in the inventory.
2. `pki-tenant-service` does not exist.

**Undo:** nothing to undo.

### Step 2: The mount, the key and the request

Not disruptive. Creates the mount and, inside OpenBao, the Tenant Service CA's key.

**Run:**

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/tenant-service-ca.yml
```

**Verify:**

1. `pki/mobile/deevnet-mobile-tenant-service-ca.csr` is written, with subject
   `O=Deevnet, OU=Mobile Site, CN=Deevnet Mobile Tenant Service CA` and an RSA 3072 key.
2. The mount exists and has no CA.
3. The Tenant Device CA reads as it did in step 1.

**Undo:** [Undo Step 2](#undo-step-2)

### Step 3: The ceremony

Offline, by the operator: [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/), with
`--ca tenant-service`.

**Verify:**

1. `deevnet-pki-transfer.sh accept` passes and writes
   `pki/mobile/deevnet-mobile-tenant-service-ca.pem`.
2. Its fingerprint is the one on paper.

**Undo:** none. A signed CA certificate cannot be withdrawn; an unused one is left uninstalled.

### Step 4: Install the CA, and the signing role

Not disruptive. Nothing can call the role yet.

**Run:**

```bash
ansible-playbook playbooks/tenant-service-ca.yml
ansible-playbook playbooks/tenant-service-ca.yml      # a second run changes nothing
```

**Verify:**

1. `GET pki-tenant-service/ca/pem` is the certificate in the inventory, and chains to the root.
2. With the automation's own token, the role signs a request for `probe.eds.mobile.deevnet.net`. The
   leaf has the subject, names and usages of a tenant service certificate, a `CA:FALSE` it did not
   take from the request, and one year.
3. The role refuses `grafana.mobile.deevnet.net`, `mobile.deevnet.net`, `*.eds.mobile.deevnet.net`,
   `example.com` and an IP address.
4. A request that asks for `CA:TRUE`, `clientAuth` and a second name gets none of them.

**Undo:** [Undo Step 4](#undo-step-4)

### Step 5: The API

Restarts the API.

**Run:**

```bash
ansible-playbook playbooks/site.yml --tags openbao --limit openbao      # the API's policy
ansible-playbook playbooks/site.yml --tags deevnet-api --limit deevnet_api
```

**Verify:**

1. `GET /version` is the new version.
2. A tenant is read through the API as before.
3. With a tenant's token, a certificate is issued for a label; with another tenant's token, the
   same path answers `404`.

**Undo:** [Undo Step 5](#undo-step-5)

### Step 6: The first tenant service

The `eds` tenant's own change, recorded in its own records. Its console moves to HTTPS.

**Verify:**

1. `openssl s_client -connect console.eds.mobile.deevnet.net:443 -CAfile deevnet-root-ca.pem
   -verify_return_error` verifies with the root alone.
2. The page opens in a browser on the trusted network with no warning.

## Verification

The Goal's seven facts, each read after step 6.

## Undo

### Undo Step 5

Set the API's version back and run the `deevnet-api` play; remove the policy path and run the
`openbao` play. Certificates already issued stay valid until they expire.

### Undo Step 4

Delete the role: `DELETE pki-tenant-service/roles/<role>`. The CA stays installed and can sign
nothing.

### Undo Step 2

Disable the mount: `DELETE sys/mounts/pki-tenant-service`, which destroys the key. Remove the
request from the inventory. Practical until step 3; after it, the Site CA has signed a certificate
for a key that no longer exists, which is harmless and stays on the paper record.

## Outcome

*Completed after the change has run.*

| When | Steps | What happened |
|---|---|---|
| | | |

### Departures from the plan

-

## Follow-ups

- [ ]
