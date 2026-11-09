---
title: "OpenBao's Keys"
weight: 5
---

# OpenBao's Keys

**Every key OpenBao uses is held in ansible-vault and imported on each build, so a rebuilt OpenBao
comes back with the same keys and nothing is restored**
([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/) §4,
[CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)). OpenBao never makes a key of its
own. The `openbao` role in `deevnet.mgmt` does the import; this page is how each key is made,
changed and checked.

| Key | Vault variable | Made by | In OpenBao |
|---|---|---|---|
| Tenant Service CA | `vault_tenant_service_ca_key` (`group_vars/all`) | `playbooks/tenant-cas.yml` | `pki-tenant-service`, default issuer |
| Tenant Device CA | `vault_tenant_device_ca_key` (`group_vars/all`) | `playbooks/tenant-cas.yml` | `pki-tenant-device`, default issuer |
| Transit key | `vault_openbao_transit_key` (`group_vars/openbao`) | `playbooks/transit-key.yml` | `transit/keys/<openbao_transit_key>` |

Each playbook refuses to replace a key the vault already holds. **A key a playbook makes exists only in
the decrypted vault file until it is encrypted, committed and pushed**: do that before anything uses
it ([Vault Operations](/docs/runbook/substrate/building-recovery/vault-operations/#secrets-a-change-produces)).

---

## The tenant CAs

**A tenant CA is its key from the vault and its certificate from the ceremony, imported together.**
The role checks the two are a pair, imports both with the Site CA (`issuers/import/bundle`), and makes
that issuer the default. A mount already serving the inventory's certificate is left alone.

**To replace one,** with the import and the check in a [work session](#a-work-session):

1. Remove both tenant CA keys from the vault (the playbook makes the pair), and run
   `ansible-playbook playbooks/tenant-cas.yml` with the vault decrypted. It writes the new keys into
   the vault and their requests to `pki/<site>/rekey/`. For one CA only, keep the other's new key and
   request unused.
2. `make vault`, commit and push.
3. Sign the request in the [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) ceremony, and accept
   the certificate.
4. Move the certificate and request into place in `pki/<site>/`, commit, and run
   `ansible-playbook playbooks/tenant-service-ca.yml` or `tenant-device-ca.yml`.

**Verify:** the mount serves the new certificate, by fingerprint:

```bash
curl -s --cacert pki/deevnet-root-ca.pem \
  https://dv02idn001v01.mobile.deevnet.net:8200/v1/pki-tenant-service/ca/pem \
  | openssl x509 -noout -subject -fingerprint -sha256
```

Then run `playbooks/tenant-service-ca-verify.yml`. What the old CA issued keeps verifying by its own
chain; its issuer stays in the mount, not the default, until a rebuild.

---

## The Transit key

**The Transit key seals the tenant secrets in the Deevnet API's database.** It is imported by
OpenBao's bring-your-own-key route: wrapped on the control node, in RAM, with an ephemeral key that is
itself wrapped with OpenBao's wrapping key. OpenBao refuses a second import onto the same name, so a
new key always has a new name.

**To move to a new key,** with steps 3 to 5 in a [work session](#a-work-session):

1. Remove `vault_openbao_transit_key` from the openbao vault, run
   `ansible-playbook playbooks/transit-key.yml`, then `make vault`, commit and push.
2. In `group_vars/all/main.yml`, set `openbao_transit_key` to a new name and
   `openbao_transit_key_previous` to the old one. Merge.
3. `ansible-playbook playbooks/openbao.yml`: it imports the new key and lets the API decrypt, and only
   decrypt, with the old one.
4. Deploy the API (`site.yml --tags deevnet-api --limit deevnet_api`). It encrypts with the new key and
   reads with the old one when the new one refuses.
5. On `dv02prv001v01`, move every stored value:

   ```bash
   sudo podman exec deevnet-api /usr/local/bin/deevnet-api reseal
   ```

   It prints what it `resealed`, what was already `current`, and what `failed` to open under either
   key, which it leaves alone. It exits non-zero if anything failed. **Run it again: it must reseal
   nothing.**
6. Empty `openbao_transit_key_previous`, merge, and run `openbao.yml` and the API deploy again.

**Verify:** every tenant reads back with `secrets_stored` true. A value that failed in step 5 is one a
tenant supplies again on its next apply
([ADR-0015](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §4).

---

## The unseal shares

**OpenBao is sealed by three Shamir shares, any two of which unseal it, and it starts sealed**
([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/) §1,
[CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/)). Share 1 is in the openbao vault as
`vault_openbao_unseal_share`. Shares 2 and 3 are the operator's, held apart from each other, never on
the kit and never on a machine that holds the vault password. No unseal material is on the identity
VM.

**A sealed OpenBao stops provisioning and nothing else.** Deployed tenants, their devices and the
broker keep running. The Deevnet API refuses tenant work before it changes anything, and its
`/readyz` answers `"openbao":"sealed"`. Every play that configures OpenBao, and the API role's OpenBao
step, stops on its first task with *OpenBao … is sealed. Nothing was changed.*

### A work session

**A visit's provisioning work runs inside a work session: OpenBao opened at its start, sealed at its
end.** Creating a tenant, renewing certificates, enrolling devices and deploying the API need it open.
From `ansible-collection-deevnet.mgmt`, with the inventory **encrypted** (Ansible asks for the vault
password instead of the vault being decrypted on disk):

```bash
make bao-status                                        # sealed or open; no vault needed
ANSIBLE_ASK_VAULT_PASS=true make bao-open              # the vault's share, and one of yours
ANSIBLE_ASK_VAULT_PASS=true make bao-open WITHOUT_VAULT=1   # two of yours, the vault unavailable
ANSIBLE_ASK_VAULT_PASS=true make bao-close             # a restart: it comes back sealed
```

A share is typed without echo and goes straight to OpenBao. A refused share resets the attempt and
changes nothing. Powering the kit off also ends the session.

### Rotating the shares

**A share that may have been exposed is replaced by rotating all three; the old ones then unseal
nothing.** In a work session:

```bash
ANSIBLE_ASK_VAULT_PASS=true make bao-rotate-shares
```

It takes two current shares, as `bao-open` does, writes three new ones to
`.openbao/<host>-shares.json` on the control node at once, and proves every pair by restart and
unseal. Then, in the operator's own terminal:

1. Store new shares 2 and 3 in place of the old ones.
2. Put new share 1 into the openbao vault with `ansible-vault edit`, so the file stays encrypted on
   disk; commit and push it through a pull request.
3. `shred -u` the shares file, then `make bao-close`.

**Never decrypt the vault, or open a shares file, inside an AI agent's session.** An agent's harness
can record a file it has seen when the file changes. A share reached a session transcript that way
during CHG-0053, and the shares were rotated.

## Logging in

**Ansible's AppRole is root-equivalent**: it writes every policy, the others' included. Its role and
secret IDs are held in the vault only (`vault_openbao_ansible_role_id`, `vault_openbao_ansible_secret_id`).

**After a first initialization, the role stops until the vault's AppRole logs in.** Initialization
writes the new AppRole and the three unseal shares to `.openbao/<host>-init.json` on the control node,
and unseals with two of them to carry on. Move the AppRole and share 1 into the openbao vault, take
shares 2 and 3 as in [The unseal shares](#the-unseal-shares), `make vault`, commit and push, and only
then delete the file. A run in
between stops and names the file; with no file, it stops and says not to reinitialize.

**Each AppRole logs in only from its own addresses** (`openbao_*_cidrs` in `group_vars/openbao`), the
ones OpenBao's audit log shows for each caller. The openbao role's own calls on the identity VM reach
OpenBao through podman's bridge, so they come from its gateway, `10.88.0.1`. A caller refused with
`unauthorized by CIDR restrictions` is calling from an address not listed.

**The API's secret ID expires after a year.** The `deevnet_api` role looks it up on each deploy and
issues a new one when fewer than 60 days remain, then destroys the old one once the API is up. **A year
with no API deploy leaves it unable to log in**, and it refuses tenant work until it is deployed again.

---

## The audit log

**Every request to OpenBao is logged**, secrets HMAC'd, to `/srv/openbao/logs/audit.log` on
`dv02idn001v01`, rotated at 50 MB with ten kept. **OpenBao refuses requests it cannot audit**: the role
stops before configuring anything when the disk under the log has less than 1 GiB free. To read who
called what:

```bash
sudo tail -200 /srv/openbao/logs/audit.log | jq -c 'select(.type=="response")
  | {time, from: .request.remote_address, role: .auth.metadata.role_name, path: .request.path, error}'
```
