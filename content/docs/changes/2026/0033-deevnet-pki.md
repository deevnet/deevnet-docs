---
title: "CHG-0033: The Deevnet PKI"
weight: -33
---

# CHG-0033: The Deevnet PKI

| | |
|---|---|
| **Date** | 2026-10-03 |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | **Planned.** The code is written, tested off the site and merged (2026-10-03), but not yet run against anything. Step 1 waits on the operator's offline session. |
| **Window** | Steps 1–3 over one or two days, nothing live changing. Steps 5–7 in one sitting. Step 8 once nothing uses the old root. |
| **Site** | mobile |
| **Systems** | Every substrate host and service: both hypervisors, the core router, `dv02idn001v01` (OpenBao), `dv02prv001v01` (the API, the state store), `dv02msg001v01` (the broker, the log bridge), `dv02obs001v01` (the log store, Grafana, downloads), `dv02nms001v01` (the Omada controller), `dv02hyp002p02` (the egress agent), the Builder. Every tenant (tdemo, eds, mabell, cdeever), the operator's computers. |
| **Automation** | `deevnet.mgmt` `playbooks/substrate-ca.yml`, `tenant-device-ca.yml`, `certs.yml`, `site.yml`, `scripts/pki/`; `deevnet.builder` `substrate_cert`, `site_trust`, `proxmox_node_cert`; `deevnet.net` `opnsense_cert`, `tenant-egress-agent.yml`; the inventory's `site_root_ca_*`; the image factory's Fedora template |
| **Risk** | High. Every TLS client changes trust anchor, and the operator's own computers cannot be updated by automation. Both roots are trusted side by side until step 8 to soften it. |
| **Related changes** | Replaces what [CHG-0031](/docs/changes/2026/0031-site-root-ca/) and [CHG-0032](/docs/changes/2026/0032-appliance-certificates/) built; CHG-0034 (device certificates, mTLS) follows |
| **Related runbooks** | [Root of Trust](/docs/runbook/root-of-trust/), [Certificates](/docs/runbook/substrate/certificates/) |

---

## Summary

Builds [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/):

- **an offline Deevnet Root CA and an offline Mobile Site CA**, made by the operator on the
  `pi-pki` machine;
- **a Substrate CA**, its key in the site's vault, which signs every substrate certificate on the
  control node, OpenBao's own listener included;
- **a Tenant Device CA**, its key inside OpenBao, ready for device certificates in CHG-0034.

It retires the ADR-0030 hierarchy: the site root whose key sat in the vault (risk R-11), the
bootstrap intermediate, and OpenBao's `pki` intermediate.

The re-root is gentle where it can be. Every trust store and every service's CA file holds **both
roots** from step 5 to step 8, so a service moves to the new chain without breaking its peers. The
old root goes only once nothing serves its chain.

## Goal

- Every substrate service and appliance serves a chain `leaf → Mobile Substrate CA → Mobile Site
  CA`, and it verifies against `deevnet-root-ca.pem` alone, by every name and address in the
  inventory.
- Every subject reads `O=Deevnet, OU=…, CN=…`.
- OpenBao's only PKI mount is `pki-tenant-device`. Its CA is the Mobile Tenant Device CA, chaining
  to the root.
- No certificate on the site depends on OpenBao, and no key above the issuing CAs is on a networked
  machine. `vault_site_root_ca_key` and `vault_site_bootstrap_ca_key` are gone.
- Hosts, templates, tenants, devices and the operator's computers trust `deevnet-root-ca.pem`, and
  no longer trust `deevnet-mobile-root-ca.pem`.

## Scope

**In:**
- the two ceremonies;
- the substrate's certificates and trust;
- OpenBao's listener and its Tenant Device CA;
- the core router;
- tenant trust;
- the downloads site, the operator's scripts and the Fedora template.

**Out:**
- issuing device certificates and the broker accepting them: CHG-0034;
- automatic renewal: ADR-0030's open questions, unchanged.

## Risk and impact

- **No tenant device is active yet**, so none loses the broker at step 6. A device flashed later
  takes `deevnet-root-ca.pem`.
- **Merged code, unrun.** The PRs merged on 2026-10-03, before the certificates exist. A
  certificate or trust run before step 4 fails at its first check (a missing CA file), before
  writing anything. Run none until then.
- **The operator's computers distrust the substrate at step 6** unless they took the new root in
  step 5. That includes the Windows browser used for the Proxmox and router GUIs.
- **OpenBao's clients pin its listener.** The `deevnet_api` role must run right after the
  `openbao` role in step 6: between the two, the API's calls to OpenBao fail.
- **The core router** keeps the GUI's certificate selection, because its certificate is replaced in
  place. CHG-0032's one manual selection is still owed, and is made in step 6 if it has not been
  already.
- **Grafana data sources** hold a copy of the CA. `make reconcile NAME=--all` rewrites them.

## Prerequisites

- [ ] The operator accepts ADR-0031's design (it stays Proposed until this change completes)
- [ ] The `pi-pki` image flashed and its hardware checks done
      ([Preparing](/docs/runbook/root-of-trust/preparing/))
- [ ] Media: two key media, one transfer media, the paper record
- [x] PRs merged 2026-10-03: `ansible-collection-deevnet.builder` #24, `.mgmt` #65, `.net` #45,
      `ansible-inventory-deevnet` #69, `deevnet-image-factory` #24, and this record (#262)
- [ ] The inventory decrypted on the Builder

## Procedure

### Step 1: The Deevnet Root CA and the Mobile Site CA

**Run** (the operator, offline):
1. [Root CA](/docs/runbook/root-of-trust/root-ca/), then [Site CA](/docs/runbook/root-of-trust/site-ca/)
   for `mobile`, in one session.
2. Bring the transfer drive to the Builder: `sudo mount LABEL=TRANSFER /mnt/transfer`, then copy
   `deevnet-root-ca.pem` and `deevnet-mobile-site-ca.pem` (certificates only) to `~/pki-inbox/`.

**Verify** (on the Builder):
1. `openssl verify -CAfile deevnet-root-ca.pem deevnet-mobile-site-ca.pem` is `OK`.
2. The subjects are exactly as the [standard](/docs/standards/certificates/) says.
3. Both SHA-256 fingerprints match the paper record, read aloud by the operator.

**Undo:** nothing online has changed. Delete the files.

### Step 2: The issuing CAs' requests

**Run** (on the Builder, inventory decrypted):

```bash
cd ansible-inventory-deevnet
cp ~/pki-inbox/deevnet-root-ca.pem pki/
cp ~/pki-inbox/deevnet-mobile-site-ca.pem pki/mobile/
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/substrate-ca.yml      # key into the vault, request to pki/mobile/
cd ../ansible-inventory-deevnet && make vault && git add pki mobile && git commit && git push   # on a branch, as a PR
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/tenant-device-ca.yml  # key inside OpenBao, request to pki/mobile/
```

The Substrate CA's key exists only in the vault: **encrypt, commit and push before step 3**.

`tenant-device-ca.yml` writes the new policies: Ansible's gains `pki-tenant-device/*`, and the API's
loses `pki/issue/platform`, which nothing calls. It enables the `pki-tenant-device` mount. Nothing
else in OpenBao changes.

**Verify:**
1. Both requests are in `pki/mobile/`.
2. The pushed `vault.yml` starts `$ANSIBLE_VAULT`.
3. Step 3's `prepare` accepts both requests.

**Undo:**
1. Delete the `ADR-0031 Substrate CA key` block from the vault, and both requests.
2. Delete the `pki-tenant-device` mount.
3. Run `playbooks/openbao.yml` from `main` to restore the policies.

### Step 3: Sign both issuing CAs

**Run:** the [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) ceremony, twice in one session:
first `--ca substrate`, then `--ca tenant-device`. The transfer media goes Builder → Pi → Builder
for each. Accept each into the inventory:

```bash
./deevnet-pki-transfer accept /mnt/transfer \
  --csr ../../../ansible-inventory-deevnet/pki/mobile/deevnet-mobile-substrate-ca.csr \
  --out ../../../ansible-inventory-deevnet/pki/mobile
# and the same for deevnet-mobile-tenant-device-ca.csr
cd ../.. && ansible-playbook playbooks/tenant-device-ca.yml   # installs the signed CA in OpenBao
```

Commit both certificates to the inventory, as a PR.

**Verify:**
1. Both `accept`s pass, and their fingerprints match the paper record.
2. The second `tenant-device-ca.yml` run reports the mount's CA is the ceremony's certificate.
3. A third run changes nothing.

**Undo:** remove the certificates. OpenBao's mount is unused until CHG-0034.

### Step 4: Publish

The PRs are merged already. **Run:**

```bash
cd ansible-collection-deevnet.builder && make publish
cd ../ansible-collection-deevnet.net && make publish
cd ../ansible-collection-deevnet.mgmt && make install-dev
```

**Verify:** `certs.yml`, `site.yml`, `openbao.yml` and `tenant-device-ca.yml` pass `--syntax-check`.

From here, any certificate the site issues comes from the Substrate CA. **Run nothing else until
step 5.**

**Undo:** publish the commit before the merges.

### Step 5: Trust both roots everywhere

**Run:**
1. Hosts:

   ```bash
   ansible-playbook playbooks/certs.yml --tags trust            # OS stores: Builder, hypervisors, management plane
   cd ../ansible-collection-deevnet.net && ansible-playbook playbooks/tenant-egress-agent.yml
   cd ../ansible-collection-deevnet.mgmt && ansible-playbook playbooks/site.yml --skip-tags vms --tags log-bridge
   ```
2. Tenants (tdemo, eds, mabell, cdeever): each CA file becomes both roots:
   `cat deevnet-root-ca.pem deevnet-mobile-root-ca.pem > deevnet-mobile-root-ca.pem.new`, then move
   it into place. `terraform plan` shows no changes.
3. The operator's computers: import `deevnet-root-ca.pem` as a trusted root, keeping the old one.

**Verify:**
1. On every host, the OS bundle holds both roots (the play checks).
2. `tenant-check.sh` passes for each tenant.

**Undo:** remove the new anchor. Nothing serves under it yet.

### Step 6: Reissue every certificate from the Substrate CA

The CA file is renamed (`deevnet-root-ca.pem`) and now holds both roots, so container configuration
changes. As in CHG-0031, this is `site.yml` per host, not `certs.yml`.

**Run**, back to back:

```bash
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02idn001v01   # OpenBao listener, Tenant Device CA
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02prv001v01   # the API (re-pins OpenBao), state store
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02msg001v01   # broker, bridge
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02obs001v01   # log store, Grafana, downloads
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02nms001v01   # Omada controller
ansible-playbook playbooks/certs.yml --tags hypervisors,router
make reconcile NAME=--all
```

On the core router, if CHG-0032's selection was never made: **System > Settings > Administration >
SSL Certificate**, choose `Deevnet site certificate (dv02cor002p01.mobile.deevnet.net)`, then set
`site_verify_opnsense: true`.

**Verify:**
1. For each service, `openssl s_client -connect <name>:<port> -showcerts -CAfile pki/deevnet-root-ca.pem`
   shows three certificates (leaf, Substrate CA, Site CA) and `Verify return code: 0 (ok)`.
2. The leaf's subject is `O=Deevnet, OU=Mobile Substrate, CN=…`.
3. `curl -fsS https://api.mobile.deevnet.net:8080/v1/version` from the Builder, with no `--cacert`.
4. The API reaches OpenBao: tenant reads succeed.
5. The bridge's health endpoint answers, and a device log line reaches the store.
6. `make reconcile` reports every tenant reconciled.
7. The router GUI, Proxmox `:8006` and the Omada controller verify in the operator's browser.

**Undo:** [Undo Step 6](#undo-step-6)

### Step 7: Tenant tooling, scripts and docs

**Run:**
1. The provider repo: `tenant-check.sh` and `install-provider.sh` embed `deevnet-root-ca.pem`, and
   `--write-ca` writes that name. Stage both onto the downloads mirror.
2. The tenant repos (tdemo, eds, mabell) and eds lightd's deploy name `deevnet-root-ca.pem`.
3. The docs: the tenant guide, the device walkthroughs, the Certificates runbook (rewritten for the
   new hierarchy), the roadmap, and ADR-0031 Accepted.
4. Rebuild the Fedora templates (`make proxmox-fedora-pve1`, `-pve2`).

**Verify:**
1. `tenant-check.sh` from the downloads site passes from `DVNTM-TD` with only `deevnet-root-ca.pem`.
2. The template build's own anchor check passes.

### Step 8: Retire the old root

Only once step 6 verifies and every tenant, device and computer trusts the new root.

**Run:**
1. Inventory:
   - `site_root_ca_previous_files: []`;
   - `site_root_ca_retired: [deevnet-mobile-root-ca.pem]`;
   - `openbao_retired_mounts: [pki]`;
   - `opnsense_cert_retired_cas: [Deevnet mobile root CA, Deevnet mobile bootstrap CA]`.
2. Delete `vault_site_root_ca_key` and `vault_site_bootstrap_ca_key` from the vault, and
   `pki/mobile/deevnet-mobile-root-ca.pem` and `-bootstrap-ca.pem`. Then `make vault`, commit and
   push.
3. Run:
   - `certs.yml`;
   - `site.yml --skip-tags vms` per host, as in step 6;
   - `tenant-egress-agent.yml`.
4. Tenants, devices and the operator's computers drop the old root.
5. Close R-11 in the risk register.

**Verify:**
1. No OS bundle holds the old root.
2. `pki` is gone from OpenBao.
3. The router lists only the three new CAs.
4. Every step 6 check still passes with only `deevnet-root-ca.pem`.
5. `certs.yml` reports `changed=0`.

## Verification

The Goal as a whole, from the Builder and from a computer on `DVNTM-TD` holding only
`deevnet-root-ca.pem`.

## Undo

### Undo Step 6

Every host still trusts the old root, and OpenBao's old `pki` mount is untouched until step 8.

1. Revert the CHG-0033 merges and publish the previous `main`.
2. Run `openbao.yml`, then `site.yml` per host, as in CHG-0031 step 5. Each role finds its
   certificate does not chain to the old root and reissues from the old intermediate.
3. Put the old self-signed listener back: delete `/srv/openbao/tls/listener*.pem` and run
   `openbao.yml` from the old code.

Tenants keep both roots until step 8, so they need nothing.

## Outcome

Not started.

## Follow-ups

- CHG-0034: device certificates through the Deevnet API, and the broker accepting them (ADR-0031
  §6).
- Untested until step 2: `tenant-device-ca.yml` against the live listener (the Tenant Device CA
  steps were tested against an OpenBao 2.6.2 dev server). Untested until step 8: the router's
  `trust/ca/del` result value.
