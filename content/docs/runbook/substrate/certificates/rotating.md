---
title: "Rotating"
weight: 6
---

# Rotating

Certificates are renewed by [Renewing](/docs/runbook/substrate/certificates/renewing/). The CAs
above them change only deliberately, in an offline ceremony, about a year before each expires
([Custody](/docs/runbook/root-of-trust/custody/) has the calendar and what each rotation reaches).

## Rotate the Substrate CA with a new key and an Issuing CA ceremony

Valid to 2031-10-04. Remove the `ADR-0031 Substrate CA key` block from the vault and the old request,
then:

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/substrate-ca.yml       # a new key into the vault, its request to pki/mobile/
cd ../ansible-inventory-deevnet && make vault      # then commit and push: the key exists nowhere else
```

Take the request through the [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) ceremony, accept
the certificate into `pki/mobile/`, then `certs.yml`. Certificates under the old Substrate CA keep
chaining to the root, so clients trust both until each is reissued; ordinary renewal moves them all
within the year.

## Rotate a tenant CA with a new key from the vault

**A tenant CA is replaced by a new key made in the vault, signed in the Issuing CA ceremony and
imported into OpenBao.** Both are valid to 2031-10-25. The steps, and how to check the result, are on
[OpenBao's Keys](/docs/runbook/substrate/building-recovery/openbao-keys/#the-tenant-cas): in short,
`playbooks/tenant-cas.yml` makes the key and request, the ceremony signs it (`--ca tenant-service` or
`--ca tenant-device`), and `tenant-service-ca.yml` or `tenant-device-ca.yml` imports the pair. Then:

```bash
ansible-playbook playbooks/tenant-service-ca-verify.yml
```

Certificates the old CA issued stay valid until they expire. Each tenant's moves to the new CA when
the tenant next renews it.

## Check what the Tenant Service CA will sign

**After any change to the signing role, ask it for what it must refuse.**
`playbooks/tenant-service-ca-verify.yml` sends a request that names a substrate host, a public name
and an address, and asks to be a CA and a client. It asks for `probe.chg0047.deevnet.net`, a
site-less name, and checks that none of the rest is in the certificate that comes back. Then it
checks that nine requests are refused: the site's zone itself, one label under the root, the root, a
wildcard, a public name alone and beside a good one, an address, a URI, and no name at all. It
issues one certificate each run, for a name under a tenant that does not exist, and deletes the key.

**The role does not refuse a substrate service's name**, such as `grafana.mobile.deevnet.net`. It
allows any name at least two labels under `deevnet.net`, so that a tenant's site-less names can be
issued. What keeps a tenant from a site's names is the Deevnet API, which refuses a tenant named
after a site or a global alias
([CHG-0054](/docs/changes/2026/0054-site-less-tenant-names/)). A role per tenant, which would let
OpenBao refuse them too, is a follow-up of that change.

## A new Site CA or root is a re-root of that scope

A new Site CA means new issuing CAs and every certificate at the site reissued; a new root means
that, at every site, and every trust store handed the new root. Run the old and new roots side by
side while services move:

1. the new root's or Site CA's ceremony, then each issuing CA's;
2. list the outgoing root in `site_root_ca_previous_files`, and run `certs.yml --tags trust`: every
   host, service and client file trusts both;
3. `site.yml --skip-tags vms --limit <host>` for each service host, and `certs.yml --tags
   hypervisors,router`: every certificate reissued;
4. once nothing serves the old chain, move it to `site_root_ca_retired`, and run the same again: the
   old anchor and files are removed everywhere.

Tenants, the embedded copies (`tenant-check.sh`, `install-provider.sh`), the VM templates and every
computer take the new root too. [CHG-0033](/docs/changes/2026/0033-deevnet-pki/) is the record of
the last re-root.
