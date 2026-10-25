---
title: "CHG-0036: OpenBao's Keys From the Vault"
weight: -36
---

# CHG-0036: OpenBao's Keys From the Vault

| | |
|---|---|
| **Date** | 2026-10-25 |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | **Complete, 2026-10-25**, with Step 5, the rebuild drill, moved to a follow-up. Every key OpenBao uses is the vault's, the role stops until an initialization is locked in, and OpenBao's access is bound and audited |
| **Window** | Unscheduled. After [CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/). One issuing-CA ceremony for both tenant CAs; one OpenBao role run; one API deploy |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao), `dv02prv001v01` (the Deevnet API), the offline ceremony machine |
| **Automation** | `deevnet.mgmt` `playbooks/openbao.yml` and `site.yml --tags deevnet-api`; the [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) ceremony |
| **Risk** | Medium. Most likely to go wrong: switching the Transit key leaves the API's stored copies unreadable until they are resealed or tenants resupply |
| **Related changes** | [CHG-0033](/docs/changes/2026/0033-deevnet-pki/) (built the Tenant Device CA inside OpenBao), [CHG-0047](/docs/changes/2026/0047-tenant-service-certificates/) (built the Tenant Service CA inside OpenBao), [CHG-0052](/docs/changes/2026/0052-sealed-openbao-is-unavailable/) (before this), [CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/) (after this) |
| **Related incidents** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) |
| **Related runbooks** | [OpenBao's Keys](/docs/runbook/substrate/building-recovery/openbao-keys/), [Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/), [OpenBao Drills](/docs/runbook/substrate/recovery/substrate-secrets-drills/) |

---

## Summary

Three keys exist only inside OpenBao: the **Tenant Device CA's** key, generated there by CHG-0033,
the **Tenant Service CA's**, generated there by CHG-0047, and the **Transit key** that seals the
Deevnet API's stored copies of tenant secrets. All three were made non-exportable, so none can be
copied out. Losing OpenBao's storage loses all three: new tenant CAs, and a database nobody can read.
This change replaces each with a key made outside OpenBao, makes the vault the authoritative copy,
and loads them into OpenBao on every build, so a rebuilt OpenBao comes back with the same keys. It
also makes the role stop until a fresh initialization is locked in, and tightens OpenBao's own access
([2026-10 review: R1, T1, R5, A4](/docs/architecture/reviews/2026-10-rebuild-and-access/#responses-so-far);
[2026-10 tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/), phase P1).

**The tenant CAs are re-keyed under names without a site**, `Deevnet Tenant Service CA` and
`Deevnet Tenant Device CA`, still signed by the Mobile Site CA, because they serve tenants at every
site ([ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/) §2,
[ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/) §4).
Devices trust the root, so none is touched. What the old Tenant Service CA issued, `eds`'s console
certificate and CHG-0047's probe certificates, runs to expiry; the Tenant Device CA has issued
nothing.

**The rule after this change:** any key OpenBao uses that can't be re-derived is held in ansible-vault
and loaded as configuration.

## Goal

- The Tenant Device CA's and the Tenant Service CA's keys are in ansible-vault, new and made outside
  OpenBao; each PKI mount holds its key, imported, and the certificate the Mobile Site CA signed for
  it under its site-less name.
- What the old Tenant Service CA issued keeps verifying: a server presents its chain, which needs
  nothing from OpenBao.
- The Transit key the API uses is in ansible-vault, imported into OpenBao; the API's stored copies
  are sealed under it.
- After a fresh initialization, the next run of the role stops until the vault's `ansible` AppRole can
  log in.
- The API's AppRole secret ID is bound to the provisioning VM's address and expires; Ansible's is bound
  to the Builder and the temporary builder.
- A file audit device records every request, on the identity VM's disk, rotated.
- The `ansible` AppRole is described as what it is: root-equivalent, held only in the vault.
- A rebuild drill: OpenBao's storage wiped and rebuilt, and both keys are back without a ceremony;
  the API reads its stored copies.

## Scope

**In scope:** the `openbao` role (PKI import, Transit import, the lock-in stop, CIDR binding, the audit
device); both tenant CAs re-keyed from vault-held keys and renamed; resealing the API's stored copies.
**Out of scope:** device certificates (CHG-0034); the build path (CHG-0037).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Stored copies unreadable after the Transit switch | the API | Import the new key under a new name, reseal every stored copy (decrypt with the old, encrypt with the new), and keep the old key until none remain; tenants' next apply resupplies anything missed |
| A key written only to a local file during the change | control node | The lock-in rule: vault, encrypt, commit, push before the next step |
| A tenant service certificate stops verifying | tenants | Verification needs only the chain the server presents; `eds`'s console checked after Step 1 and after Step 5 |
| The audit device fills the disk | identity VM | Rotation, and a size check in the role |
| A CIDR binding locks Ansible out | OpenBao | Bind to every address the control node uses, including the temporary builder's; the recovery key is the way back |

## Prerequisites

- [ ] Vault decrypted; collections built
- [ ] The offline ceremony machine, with its bootloader reset ([Ceremony](/docs/runbook/root-of-trust/ceremony/))
- [ ] Each tenant's state to hand, in case a stored copy has to be resupplied

## Procedure

### Step 1: Both tenant CAs from vault-held keys

For each of the Tenant Device CA and the Tenant Service CA, generate a key and a request on the
control node, under the CA's site-less name, write the key into the vault and lock it in. Sign both
requests in one [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) ceremony, then have the role
import each signed certificate with its key into its PKI mount and make it the default issuer.

**Verify:** each mount's default issuer has a key, chains to the Mobile Site CA, carries its
site-less name, and its key matches the vault's; `eds`'s console still verifies.

### Step 2: The Transit key from the vault

Generate a key, vault it, import it into OpenBao's Transit engine under a new name, point the API at
it, and reseal every stored copy.

**Verify:** the API's `/readyz` is `200`; every tenant's reconcile succeeds; no stored copy is under
the old key.

### Step 3: The lock-in stop

After an initialization, the role checks the vault's `ansible` AppRole can log in, and stops with a
message naming `.openbao/<host>-init.json` if not.

**Verify:** on a scratch run with deliberately stale vault values, the role stops with that message.

### Step 4: OpenBao's own access

CIDR-bind both AppRoles' secret IDs; give the API's an expiry; enable a file audit device with
rotation; correct the `ansible` AppRole's description.

**Verify:** a login from another host is refused; requests appear in the audit file.

### Step 5: The rebuild drill

Wipe OpenBao's storage and rebuild it from the role. Lock in its initialization (the stop in Step 3
enforces it).

**Verify:** both tenant CAs and the Transit key are the vault's; the API reads its stored copies
with no tenant resupplying anything.

## Verification

Step 5 passes, V3 and V12 of the
[tenant PKI validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan) pass,
and the documents describe the new state: ADR-0016's conflict row and ADR-0033's open question 2 are
closed, and *Build-Time Secrets* and the OpenBao drills page say what is true.

## Undo

Until Step 5, each step reverses: the previous tenant CAs and Transit key stay in OpenBao until
the end. After Step 5, the old keys are gone by design.

## Outcome

### Step 1: keys and certificates, 2026-10-25

`deevnet.mgmt` `playbooks/tenant-cas.yml`
([#87](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/87)) generated both keys,
RSA 3072, on the control node and wrote them into the mobile vault as
`vault_tenant_service_ca_key` and `vault_tenant_device_ca_key`. They were encrypted, committed and
pushed ([inventory #85](https://github.com/deevnet/ansible-inventory-deevnet/pull/85)) before the
ceremony. `deevnet-pki-transfer.sh` was changed to expect the site-less CNs; the offline signing
tool needed no change. Both requests were then signed by the Mobile Site CA in one Issuing CA
ceremony, one round trip of the transfer drive each, and accepted against the inventory's root and
Site CA.

| CA | Subject | Valid | SHA-256 fingerprint |
|---|---|---|---|
| Tenant Service CA | `O=Deevnet, OU=Mobile Site, CN=Deevnet Tenant Service CA` | 2026-10-25 to 2031-10-25 | `68:C7:0F:24:9A:F9:AC:6A:1F:31:B7:65:0E:6D:E1:42:B5:7F:59:79:ED:E5:FC:A6:08:D0:39:05:C1:E0:70:F3` |
| Tenant Device CA | `O=Deevnet, OU=Mobile Site, CN=Deevnet Tenant Device CA` | 2026-10-25 to 2031-10-25 | `52:E3:27:08:50:98:D4:55:1C:4D:AB:DF:73:7E:CD:8F:FF:29:34:9E:41:6D:CF:9F:AD:CE:08:C9:E8:B4:74:14` |

Both are `CA:TRUE, pathlen:0`, Certificate Sign and CRL Sign. They are in `pki/mobile/rekey/`; the
certificates in `pki/mobile/` are still the ones OpenBao holds.

### Step 1: the import, 2026-10-25

`deevnet.mgmt` [#89](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/89) changed
`issuing_ca.yml`: OpenBao no longer generates a CA key. The role checks the vault's key is the
inventory certificate's, imports both with the Site CA (`issuers/import/bundle`), and makes that
issuer the default; a mount already serving the certificate is left alone. Before the run it was
tested against a throwaway OpenBao 2.6.2 set up as the live mounts were: a mismatched key stopped
before importing, the import switched the default, a second run changed nothing, and a leaf from
the new issuer chained to the root.
[Inventory #86](https://github.com/deevnet/ansible-inventory-deevnet/pull/86) put the new
certificates in place. Then `playbooks/tenant-service-ca.yml`, `tenant-device-ca.yml` and
`tenant-service-ca-verify.yml` were run.

**Verify:** both mounts serve the ceremony's certificates, by fingerprint (the table above).
`console.eds.mobile.deevnet.net`, issued by the old Tenant Service CA, still verifies against the
root alone through its own chain. The old issuers stay in their mounts, not the default.

### Step 2: the Transit key, 2026-10-25

`deevnet.mgmt` `playbooks/transit-key.yml` made a 32-byte key into the openbao vault
(`vault_openbao_transit_key`), committed and pushed before anything used it
([inventory #87](https://github.com/deevnet/ansible-inventory-deevnet/pull/87)). The `openbao` role
([#90](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/90)) imports it as
`tenant-secrets-v2` by OpenBao's bring-your-own-key route: wrapped on the control node, in RAM,
with an ephemeral AES key that is itself wrapped with OpenBao's wrapping key. A key already there
must be an imported one. While values moved, the API's policy could also decrypt, and only
decrypt, with the old key.

API v0.14.0 ([deevnet-provisioning-api#34](https://github.com/deevnet/deevnet-provisioning-api/pull/34))
reads with the previous key when the current one refuses a ciphertext, and adds
`deevnet-api reseal`, run in the API's container:

| Run | Result |
|---|---|
| Before | `eds`, `tdemo`, `mabell` and `cdeever` read back with their secrets stored, through the fallback |
| `reseal` | 26 values moved: each tenant's TSIG, state, two log tokens and dashboard password, and 6 Wi-Fi keys. None failed |
| `reseal` again | 26 current, none moved |
| After | every tenant reads back with its secrets stored |

Then `openbao_transit_key_previous` was emptied
([inventory #88](https://github.com/deevnet/ansible-inventory-deevnet/pull/88)), dropping the old key
from the API's policy and environment. The old key, `tenant-secrets`, stays in OpenBao unused until
the rebuild drill.

Before the run, it was all tested against throwaway OpenBao 2.6.2 and PostgreSQL stores: a second
OpenBao given the same key decrypted what the first had encrypted, and with the old key deleted,
every resealed secret still opened.

### Step 3: the lock-in stop, 2026-10-25

`tasks/ansible_login.yml` ([#92](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/92)),
used wherever the role logs in as Ansible: a refused login stops the run, naming
`.openbao/<host>-init.json` and the vault variables to move when that file is there, and saying not
to reinitialize when it is not. A file left after the vault's AppRole logs in is reported.

**Verify:** against a throwaway OpenBao 2.6.2, with stale vault values and an init output, the role
stopped with that message; with stale values and none, it stopped and said not to reinitialize; with
good values it logged in, and reported a file left behind.

### Step 4: OpenBao's own access, 2026-10-25

**The audit device** ([#93](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/93)):
every request to `/srv/openbao/logs/audit.log` on the identity VM, secrets HMAC'd, rotated at 50M
with ten kept, and the role stops when the disk under it has under 1 GiB. It is declared in
`openbao.hcl`: OpenBao 2.6.2 refuses to enable an audit device through its API.

**The bindings** ([#95](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/95),
[inventory #89](https://github.com/deevnet/ansible-inventory-deevnet/pull/89)), from the addresses
the audit log showed for each caller, not where each was thought to be:

| AppRole | Logs in from |
|---|---|
| `deevnet-api` | `10.20.25.20`, the API's host |
| `ansible` | `10.88.0.1`, podman's bridge on the identity VM, for the role's own calls; the Builder, `10.20.99.95`; the temporary builder, `10.20.99.97` |
| `image-factory` | the Builder and the temporary builder |

The role's calls on the identity VM reach OpenBao through podman's bridge, so anything on that host
shares `10.88.0.1`: that binding is only as narrow as the host.

**The API's secret ID expires after a year.** The `deevnet_api` role looks it up rather than trying
it, since the binding refuses a login from the Builder, and issues a new one when OpenBao does not
know it, it has no expiry, or fewer than 60 days remain; it destroys the one replaced once the API
is up on the new one. The `ansible` AppRole is described as root-equivalent, held in the vault only.

**Verify:** the deploy looked up the API's secret ID, issued one with an expiry and destroyed the
old one, and the API logged in from `10.20.25.20`; every tenant reads back. The API's secret ID
tried from the Builder was refused: `source address "10.20.99.95" unauthorized by CIDR restrictions
on the role`.

### Departures from the plan

- **Staging v0.14.0 filled the Builder's `/home` again**: the build context carried every image
  tarball in the repository's `bin/`. They were moved out, and a `.containerignore` keeps them out
  from the next release
  ([deevnet-provisioning-api#36](https://github.com/deevnet/deevnet-provisioning-api/pull/36)).
- **The audit device was deployed before its PR was merged.** The control node's checkout was left
  on the PR's branch when `openbao.yml` was run for another step. It was reviewed and merged after,
  with no difference from what ran.
- **Retiring the old Transit key failed once**: the `deevnet_api` role refused the empty
  `OPENBAO_TRANSIT_KEY_PREVIOUS`, because it asserts every setting is non-empty
  ([#94](https://github.com/deevnet/ansible-collection-deevnet.mgmt/pull/94) adds it only when set).
- **A secret ID that expires needs a deploy within the year.** If none happens, the API cannot log
  in and refuses tenant work until it is redeployed.
- **Step 5, the rebuild drill, is a follow-up, not done here.** The owner chose to finish the
  tenant PKI's other changes first. Steps 1 to 4 were each verified on the live site, and the rebuild
  itself was proven on throwaway OpenBao stores: a second store given the vault's Transit key opened
  what the first sealed. The drill's procedure is written
  ([OpenBao Drills](/docs/runbook/substrate/recovery/substrate-secrets-drills/)).
- **Step 1 ran before CHG-0052 was deployed.** Making and signing the keys changes nothing that
  runs, so it does not need the API's sealed handling; the steps that touch OpenBao still wait for
  it.

## Follow-ups

- **Run the rebuild drill** ([OpenBao Drills](/docs/runbook/substrate/recovery/substrate-secrets-drills/)).
  It also removes the old Transit key, `tenant-secrets`, and the old tenant CAs' issuers, which stay in
  OpenBao unused until then.
- **The image-factory AppRole's credentials are issued only when the vault has none**, so after a
  rebuild they must be emptied by hand first. The role should notice OpenBao does not know them, as
  the `deevnet_api` role now does for the API's.

## To discover

- ~~OpenBao's exact mechanism for importing a Transit key and a PKI issuer with its key.~~ Found
  by testing against OpenBao 2.6.2, the running version, before any live run: a PKI issuer and its
  key import together through `issuers/import/bundle`, which leaves the default issuer alone and
  is idempotent; a Transit key imports through `transit/keys/<name>/import`, wrapped as above,
  and a second import onto the same name is refused.
- ~~Whether the API can reseal its stored copies itself, or needs a one-off tool.~~ Found while
  building: a subcommand of the API's own binary, run in its container, `deevnet-api reseal`.
- ~~Whether CIDR binding of secret IDs behaves as expected through the routing between the Builder
  and the identity VM.~~ Found by the audit log: the routed callers keep their own addresses; the
  role's calls on the identity VM itself arrive from podman's bridge gateway.
