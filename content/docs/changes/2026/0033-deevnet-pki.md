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
| **Status** | **Complete** 2026-10-05. Every substrate service, appliance and tenant tool trusts the Deevnet Root CA alone; the ADR-0030 root, its keys and its intermediates are retired (R-11 closed); the Fedora templates and the `pi-pki` image are rebuilt. |
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
      ([Root and Site CA Ceremony](/docs/runbook/root-of-trust/ceremony/))
- [ ] Media: two key media, one transfer media, the paper record
- [x] PRs merged 2026-10-03: `ansible-collection-deevnet.builder` #24, `.mgmt` #65, `.net` #45,
      `ansible-inventory-deevnet` #69, `deevnet-image-factory` #24, and this record (#262)
- [ ] The inventory decrypted on the Builder

## Procedure

### Step 1: The Deevnet Root CA and the Mobile Site CA

**Run** (the operator, offline):
1. The [Root and Site CA Ceremony](/docs/runbook/root-of-trust/ceremony/), path 1,
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
./deevnet-pki-transfer.sh accept /mnt/transfer \
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

Steps 1–3 on 2026-10-04. The offline steps ran on the `pi-pki` machine with
`deevnet-pki-ceremony.sh` (path 1, then path 3); the online steps ran on the Builder.

| Certificate | SHA-256 fingerprint | Valid to |
|---|---|---|
| Deevnet Root CA | `F6:8A:BD:B3:1E:A5:6D:0A:88:1F:31:28:56:8A:4C:14:B0:3A:3F:5C:3F:38:CC:F1:7C:C4:F0:09:8B:EB:94:52` | 2046-10-04 |
| Deevnet Mobile Site CA | `CD:E7:FF:FC:F0:83:7B:CE:E7:D6:64:DA:59:86:28:54:DC:4B:A7:F6:D2:BC:B7:34:26:3E:79:F7:11:4A:3A:1E` | 2036-10-04 |
| Deevnet Mobile Substrate CA | `86:EE:AB:CB:F9:5F:B7:A8:B0:90:C9:62:E2:6C:AC:D1:08:25:0F:D4:5E:4D:38:0D:30:95:8A:7D:D7:3F:5F:23` | 2031-10-04 |
| Deevnet Mobile Tenant Device CA | `66:05:74:BC:62:60:B8:80:BA:93:96:79:10:31:56:A3:67:D7:21:BA:8E:43:4D:6C:42:3E:A0:05:4D:9B:79:6A` | 2031-10-04 |

Each fingerprint was checked against the paper record. The Site CA carries the name constraints
(ADR-0031 §2). The issuing CAs were each checked against their request's key and chained to the
root through the inventory's Site CA. OpenBao's `pki-tenant-device` mount issues from the Tenant
Device CA (inventory #70, #71).

Steps 4–6 and 8 on 2026-10-04 and 2026-10-05, from the Builder.

**Step 4.** The collections published; the root put on the artifact server
(`keys/pki/deevnet-root-ca.{pem,crt}`).

**Step 5.** Both roots trusted on all 11 hosts' OS stores (each run's own check), by the egress agent
and the log bridge, and in tdemo's, eds's and mabell's CA files and eds's lightd. The operator's
Windows computer took the new root.

**Step 6**, in this order:
1. **the Deevnet API**, with a two-root CA file, so its calls reached every service whichever chain
   it served;
2. **both hypervisors**, verified by every name and address;
3. **OpenBao's listener**, then the API again to pin it; OpenBao's clients now pin the root itself;
4. **the Omada controller** and **the core router**; the operator chose the router's certificate in
   its GUI, CHG-0032's outstanding step, and `site_verify_opnsense` turned on (inventory #72): every
   client of the three appliances verifies;
5. **the state store**, **the broker** and **the observability host** (log store, Grafana,
   downloads); eds's lightd reconnected to the broker on its own;
6. `make reconcile NAME=--all`, rewriting every tenant's Grafana data sources.

**Step 8**, straight after: the operator judged no waiting period was needed, since the old root had
never been trusted where it mattered. The old anchor removed from all 11 hosts' bundles; OpenBao's
`pki` mount deleted; the router's old CAs deleted; downloads serves only `deevnet-root-ca.pem`, and the
provider's scripts embed the new root (provider #16); the old root and bootstrap keys deleted from
the vault (inventory #73). Afterwards `tenant-check.sh`, downloaded from the site, verified all six
site services with the Deevnet Root CA alone.

**Step 7** on 2026-10-05:
- **The tenant repos** tdemo (#12), eds (#12) and mabell (its open PR #1) name `deevnet-root-ca.pem`,
  and each checkout holds the new root alone. In each, `terraform init -reconfigure` reached the
  state store and `plan` refreshed through the API. eds and mabell plan output changes only. tdemo's
  plan carries older drift between its reference code and its live state, unrelated to this change.
- **eds's lightd** redeployed with the new file. It logged `connected to broker` over TLS with the
  Deevnet Root CA as its only anchor, and the old files were removed from `/opt/eds`.
- **The Fedora templates** rebuilt on both hypervisors, server and tenant flavors. Each build's own
  check found `Deevnet Root CA` among the store's anchors. The superseded templates were removed.
- **The `pi-pki` image** rebuilt from `deevnet.mgmt` `2b607ef`, which carries the chain-check fix,
  and published (SHA-256 `ab4b4bcbe7328a6cd391888e21d6a4312ebdde5d502502ac13cb128e82fbbadf`). The
  scripts inside it were compared with the collection's byte for byte.

### Departures from the plan

- **The ceremony machine took several image builds to boot and run**, each fix in the image factory:
  - the console login was never enabled (stock Pi OS turns it on only when its user wizard finishes);
  - a boot-time fsck, and the stock first-boot resize, failed under the read-only overlay;
  - `systemd-firstboot` was masked.
- **The first Root CA attempt was discarded.** The key drive dropped off the Pi's USB bus when the
  transfer drive was plugged in, while the key drive's encrypted volume was open. A full `badblocks
  -w` pass on the Builder found the drive sound. The script now asks for both drives before opening
  either, and checks and recovers drives before every write.
- **Name constraints were added to the Site CA before the root was made** (a review of what a reader
  would call an obvious gap). They are not marked critical, so mbedTLS devices still connect.
- **The ceremony script gained path 3** (signing issuing CAs). Its first run on the Pi failed to
  recognize the key drive: as the `pki` user, `blkid` cannot read a raw drive. The script now uses
  `sudo blkid`. Tests run as a non-root user with an empty `blkid` cache reproduce the failure and the
  fix.
- **`tenant-device-ca.yml` needed `become`** on its first live run (mgmt #72).
- **The PRs merged before step 1, not at step 4**, at the operator's request. No certificate or trust
  play ran in between.
- **Only one key drive so far.** The backup key drive waits for a third USB drive. Until then each
  offline key exists once.
- **Two reissue checks passed that should have failed.** `openssl verify -CAfile` also loads the
  system trust store, which since step 5 held the old root, so the API's old certificate "chained to
  the new root" and was not reissued. Every check in the roles and ceremony tools now passes
  `-no-CApath -no-CAstore` (builder #25, mgmt #75); the same flaw had let `deevnet-pki-transfer.sh
  accept` trust a chain to any public CA.
- **`substrate_cert` read an undefined variable** (`substrate`, where the inventory has
  `deevnet_substrate`), hidden by a test that defined it (builder #26).
- **`--tags` would have skipped recreating containers**: a tag selects an `include_role` but not the
  tasks it includes. Roles were run on their own, and the runbook now says `--limit`.
- **The API and the hypervisors moved together, before the rest of step 6**: the API trusted only
  the old root, so moving Proxmox alone would have cut it off.
- **OpenBao's role and `site_cert` both set its `tls` directory**, so every run changed it (mgmt #76).
- **The old root on the operator's computer was in the Intermediate store**, where Windows never
  trusts it; the runbook now says to choose Trusted Root explicitly.
- **The template build ran Packer with no credentials** when the inventory was vaulted: the
  Makefile's `eval "$(pve-creds ...)"` hid the fetch's failure. A failed fetch now stops the build
  (image factory #32).
- **tdemo had no `.backend.env`.** It was rebuilt from the `state_backend` output kept in tdemo's
  `terraform.tfstate.backup`.

## Follow-ups

- Tenant workloads cloned before step 7 (`tdemo-1`, eds's `services`, cdeever's) hold only the
  retired root in their OS trust store. They take the new one when replaced. Nothing on them uses
  the OS store for a site service today: eds's lightd names its CA file.
- The `cdeever` tenant's checkout takes `deevnet-root-ca.pem` from the downloads site.
- The backup key drive, at the first rotation drill.

- [CHG-0034](/docs/changes/2026/0034-device-certificates/): device certificates through the Deevnet API, and the broker accepting them (ADR-0031
  §6).
- Untested until step 2: `tenant-device-ca.yml` against the live listener (the Tenant Device CA
  steps were tested against an OpenBao 2.6.2 dev server). Untested until step 8: the router's
  `trust/ca/del` result value.
