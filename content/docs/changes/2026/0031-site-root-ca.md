---
title: "CHG-0031: The Site Root and Its Intermediate"
weight: -31
---

# CHG-0031: The Site Root and Its Intermediate

| | |
|---|---|
| **Date** | 2026-10-02 |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | **In progress.** Step 1 done 2026-10-02: the site root and the bootstrap intermediate exist, keys encrypted and pushed. Step 2 done 2026-10-02: code merged, collections published. Steps 3 onward not started. |
| **Window** | Steps 2–7 in one sitting; tenants are without a working CA from step 5 until step 6 |
| **Site** | mobile |
| **Systems** | `dv02idn001v01` (OpenBao), `dv02prv001v01` (the API, the state store), `dv02msg001v01` (the broker, the log bridge), `dv02obs001v01` (the log store, Grafana, downloads), `dv02hyp002p02` (the egress agent), the Builder and both hypervisors (trust store), the tdemo, eds, mabell and cdeever tenants, the eds workload |
| **Automation** | `deevnet.mgmt` `playbooks/site-root-ca.yml`, `openbao.yml`, `site.yml`, `certs.yml`, `make reconcile`; `deevnet.builder` `site.yml`, `make publish`; `deevnet.net` `tenant-egress-agent.yml`; inventory `ansible-inventory-deevnet/mobile` |
| **Risk** | Medium — every TLS client changes trust anchor at once, and tenants holding the old CA fail verification until they take the new root |
| **Related changes** | [CHG-0030](/docs/changes/2026/0030-state-store-tls/) (the last service put on the site CA); CHG-0032 (the appliances, next) |
| **Related incidents** | [INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/) (a rebuilt OpenBao re-rooted the site) |
| **Related runbooks** | [OpenBao Drills](/docs/runbook/substrate/recovery/substrate-secrets-drills/), [Tenant Admission](/docs/runbook/substrate/tenant-admission/) |

---

## Summary

Builds [ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/) §1–§2 and
§4–§7, everything but the appliances.

Today OpenBao's `pki/` mount holds a root it generated itself, `CN=Deevnet mobile internal CA`, and
six Platform services serve 90-day certificates from it. Tenants and scripts trust it as
`site-ca.pem`. Rebuilding OpenBao without its data re-roots the site (INC-0003).

After this change:
- **The root is offline.** `CN=Deevnet mobile root CA`, P-256, valid to 2046-10-02, key in the
  inventory vault. It is the only trust anchor, named `deevnet-mobile-root-ca.pem` everywhere.
- **OpenBao issues from an intermediate under it**, `CN=Deevnet mobile intermediate CA`, whose key
  OpenBao generated and keeps. A rebuilt OpenBao gets a new intermediate; nobody gets a new CA.
- **Services serve one-year certificates as leaf + intermediate**, laid down by the roles that build
  them and renewed by `certs.yml`.
- **The Builder, the hypervisors, every management-plane VM and the VM template trust the root** at
  the OS level.
- **A bootstrap intermediate exists for CHG-0032** to sign the core router and the hypervisors with.

## Goal

- `curl https://api.mobile.deevnet.net:8080/` from the Builder verifies with **no** `--cacert`.
- Every service presents two certificates, leaf then `CN=Deevnet mobile intermediate CA`, and
  `openssl verify -CAfile deevnet-mobile-root-ca.pem` accepts each: API `:8080`, state store `:9000`,
  broker `:8883`, log store `:8427`, Grafana `:3000`, downloads `:8443`.
- Each leaf is valid for a year.
- `https://downloads.mobile.deevnet.net:8443/deevnet-mobile-root-ca.pem` serves the root, SHA-256
  `68:D5:C9:8E:3D:2E:B2:DF:B6:1B:99:E4:F3:4D:F9:D3:B4:65:C3:66:34:97:30:97:36:B7:7B:60:C4:15:2C:6B`.
- `tenant-check.sh` passes for each tenant, and `terraform plan` works from tdemo, eds and mabell.
- Device logs still reach the log store through the bridge, and Grafana's data sources answer for
  each tenant.
- A second run of `certs.yml` changes nothing.

## Scope

**In scope:**
- The root and bootstrap intermediate (`site-root-ca.yml`).
- OpenBao's intermediate (`openbao` role).
- The six services' certificates (`site_cert` role), the log bridge's and egress agent's root.
- The root in the OS trust store (`site_trust` role) and in the Fedora template.
- The rename to `deevnet-mobile-root-ca.pem`: tenant repositories, scripts, downloads.
- On the Pi, deevnet-kit exports its own CA as `deevnet-kit-ca.pem`.

**Out of scope:**
- Proxmox, the core router and the Omada controller (CHG-0032).
- OpenBao's own listener, PowerDNS's API, the artifact server (ADR-0030 open question 3).
- Automatic renewal and expiry monitoring (ADR-0030 open questions 1–2).

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| Tenants holding the old CA fail verification from step 5 | laptops | Steps 5 and 6 run back to back; downloads serves the new root, under its old names too, from step 5 |
| Grafana's data sources carry the old CA as content and stop reaching the log store | obs | Step 5 reconciles every tenant, which rewrites them with the root |
| VerneMQ sends only the leaf, so clients cannot build the chain | msg | Step 5 checks that the broker serves two certificates. If it serves one, the fallback is a `cafile` holding root + intermediate (a role change, then re-run) |
| MinIO does not serve the chain from `public.crt` | prv | Step 5 checks the same; MinIO documents a chain in `public.crt`, but that is to be seen, not assumed |
| A service certificate is written before OpenBao issues under the root | any | `site_cert` refuses to write a certificate that does not chain to the root; step 3 runs first |
| The root key is lost | inventory | Encrypted, committed and pushed before anything was signed with it (step 1) |
| The test builder VM is off | `dv02bld002v01` | Trust plays run with `--limit '!dv02bld002v01'` |

## Prerequisites

- [x] ADR-0030 merged (#236, #237)
- [x] Step 1 done
- [ ] PRs merged (all `chg-0031-*`): `ansible-collection-deevnet.mgmt`, `.builder`, `.net`,
      `ansible-inventory-deevnet`, `terraform-provider-deevnet`, `deevnet-tenant-tdemo`,
      `deevnet-provisioning-api` (deevnet-kit), `deevnet-image-factory`; eds and mabell's own
- [ ] Vault decrypted on the control node

## Procedure

### Step 1: The site root and bootstrap intermediate

**Done 2026-10-02.** `site-root-ca.yml` made both on the control node; the inventory was encrypted,
committed and pushed (`ansible-inventory-deevnet` `b0e18bc`). Nothing live changed.

**Run** (in `ansible-collection-deevnet.mgmt`, inventory decrypted):

```bash
ansible-playbook playbooks/site-root-ca.yml
cd ../ansible-inventory-deevnet && make vault   # then commit and push
```

**Verify:** `openssl verify -CAfile pki/mobile/deevnet-mobile-root-ca.pem pki/mobile/deevnet-mobile-bootstrap-ca.pem`
is `OK`, and the pushed `vault.yml` starts `$ANSIBLE_VAULT`.

**Undo:** remove both `.pem` files and both `vault_site_*` keys, then commit.

### Step 2: Publish the collections

**Run:**

```bash
cd ansible-collection-deevnet.builder && make publish   # deevnet.builder.site_trust, used by mgmt
cd ../ansible-collection-deevnet.mgmt && make install-dev
```

**Verify:** `ansible-galaxy collection list deevnet.builder` shows the new build, and
`ansible-playbook playbooks/certs.yml --syntax-check` passes.

**Undo:** publish the previous `main`.

**Done 2026-10-02.** Merged mgmt #59, inventory #63, builder #21, image-factory #19 and this record
(docs #238); `make publish` installed `deevnet.builder` with `site_trust`, and `certs.yml`, `site.yml`
and `openbao.yml` pass `--syntax-check`. Before step 3, OpenBao's default issuer is
`a5679c07-dbe3-9ac2-a0eb-bfe7f31d7412` (`drill-rotated`, the internal root the 2026-09-17 drill made):
[Undo Step 3](#undo-step-3) sets it back.

### Step 3: OpenBao issues from the intermediate

**Run:**

```bash
ansible-playbook playbooks/openbao.yml
```

**Verify:**
1. The play's own check passes: `pki/ca/pem` verifies against the root.
2. `pki/config/issuers` names the new issuer as default; the old root's issuer is still listed.
3. Services are untouched: each still serves its old certificate, so nothing has broken yet.

**Undo:** [Undo Step 3](#undo-step-3)

### Step 4: The OS trust stores

**Run:**

```bash
ansible-playbook playbooks/certs.yml --tags trust --limit '!dv02bld002v01'
```

**Verify:** on each host, `openssl verify /etc/pki/ca-trust/source/anchors/deevnet-mobile-root-ca.pem`
(Proxmox: `/usr/local/share/ca-certificates/deevnet-mobile-root-ca.crt`) is `OK`. The play checks it.

**Undo:** remove the anchor file and run `update-ca-trust extract` / `update-ca-certificates`. Nothing
depends on it yet.

### Step 5: Reissue every service

The rename changes container configuration (VerneMQ's `cafile`, MinIO's `SSL_CERT_FILE`, the API's
CA paths, the bridge's), so this is `site.yml`, not `certs.yml`. Each role finds its certificate no
longer chains to the root, reissues, and restarts.

**Run**, back to back:

```bash
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02prv001v01   # API, state store
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02msg001v01   # broker, bridge
ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02obs001v01   # log store, Grafana, downloads
cd ../ansible-collection-deevnet.net && ansible-playbook playbooks/tenant-egress-agent.yml
cd ../ansible-collection-deevnet.mgmt && make reconcile NAME=--all
```

**Verify:**
1. For each service, `openssl s_client -connect <name>:<port> -showcerts` shows **two** certificates,
   and `Verify return code: 0 (ok)` with `-CAfile` the root. Broker and state store first: see Risk.
2. `curl -fsS https://api.mobile.deevnet.net:8080/v1/version` from the Builder with no `--cacert`.
3. The downloads role's check passes: every CA name it serves is the inventory's root.
4. The bridge's health endpoint answers, and a device log line reaches the store.
5. `make reconcile` reports every tenant reconciled; each tenant's Grafana data sources pass
   **Save & test**.
6. The egress agent's next run succeeds (`journalctl -u deevnet-egress-agent`).

**Undo:** [Undo Step 5](#undo-step-5)

### Step 6: The tenants

Each tenant replaces `site-ca.pem` with the root, under its new name, once.

**Run**, for tdemo, eds and mabell (in each tenant directory, after its PR merges):

```bash
curl -fsSLk -O https://downloads.mobile.deevnet.net:8443/deevnet-mobile-root-ca.pem
openssl x509 -in deevnet-mobile-root-ca.pem -noout -fingerprint -sha256   # 68:D5:C9:8E:...:2C:6B
rm -f site-ca.pem
terraform init -reconfigure     # tdemo and eds: the backend's custom_ca_bundle changed
terraform plan                  # no changes
```

Then eds's workload: regenerate `deploy/kit.env` from the outputs and `make units` in `deploy/`, so
lightd mounts the root. cdeever is the operator's own tenant on the Mac: the same steps there.

**Verify:** `tenant-check.sh` passes from `DVNTM-TD`; `terraform plan` shows no changes; eds's lights
respond.

**Undo:** keep the old `site-ca.pem` beside the new file until step 7 verifies.

### Step 7: Scripts, docs, downloads

**Run:**
1. Stage the provider's `install-provider.sh` and `tenant-check.sh` onto the downloads mirror.
2. Merge the docs PR that renames the CA across the tenant and runbook pages.
3. Run `certs.yml` once more.

**Verify:** `certs.yml` reports `changed=0`; `segment-check.sh DVNTM-TD` passes from a computer on
`DVNTM-TD`.

## Verification

The Goal, as a whole: from the Builder without `--cacert`, and from a laptop on `DVNTM-TD` with only
`deevnet-mobile-root-ca.pem`.

## Undo

### Undo Step 3

The old root is still an issuer on the mount. Set it back as the default:

```bash
# POST pki/config/issuers as Ansible's AppRole, with the id it listed before step 3
curl --cacert .openbao/dv02idn001v01-listener.pem -H "X-Vault-Token: $T" \
  -d '{"default":"a5679c07-dbe3-9ac2-a0eb-bfe7f31d7412"}' https://bao.mobile.deevnet.net:8200/v1/pki/config/issuers
```

OpenBao issues from the old root again. Nothing else changed in step 3.

### Undo Step 5

Undo step 3, then deploy each service from the commit before the CHG-0031 merges. The old roles
compare the host's CA with `pki/cert/ca`, which is the old root again, so they reissue from it.
Tenants keep their old `site-ca.pem`.

## Outcome

To be written when the change completes.

### Departures from the plan

- **The PKI certificates moved out of the inventory directory** (step 2). Step 1 wrote them to
  `mobile/pki/`, and Ansible parses every file there as an inventory source: every run warned five
  times that it could not parse them (hosts still loaded). They are at `pki/mobile/` at the inventory
  repository's root (inventory #64, mgmt #60, image-factory #20).

## Follow-ups

- CHG-0032: Proxmox, the core router and the Omada controller on site certificates, signed by the
  bootstrap intermediate (Proxmox, the router) and OpenBao (Omada); clients stop skipping verification.
- Rebuild the Fedora template so new clones carry the root (the template change is merged; the build
  is not part of this window).
- Release deevnet-kit with the `deevnet-kit-ca.pem` export, and rebuild the Pi image.
- Retire the old root's issuer from the `pki/` mount once nothing it signed is in service.
- Remove the old download names (`/deevnet-mobile-ca.pem`, `/site-ca.pem`) after one release.
