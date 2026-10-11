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

## Rotate the Tenant Device CA inside OpenBao

Valid to 2031-10-04. Remove its request and certificate from `pki/mobile/`, then:

```bash
ansible-playbook playbooks/tenant-device-ca.yml -e openbao_tenant_device_rotate=true
```

It makes a new key and request inside OpenBao. Sign it in the Issuing CA ceremony, accept it, and run
`tenant-device-ca.yml` again to install it.

## Rotate the Tenant Service CA inside OpenBao

Valid to 2031-10-11. Remove its request and certificate from `pki/mobile/`, then:

```bash
ansible-playbook playbooks/tenant-service-ca.yml -e openbao_tenant_service_rotate=true
```

It makes a new key and request inside OpenBao. Sign it in the Issuing CA ceremony
(`--ca tenant-service`), accept it, and run `tenant-service-ca.yml` again to install it. Then check
what it signs:

```bash
ansible-playbook playbooks/tenant-service-ca-verify.yml
```

Certificates the old CA issued stay valid until they expire. Each tenant's moves to the new CA when
the tenant next renews it.

## Check what the Tenant Service CA will sign

**After any change to the signing role, ask it for what it must refuse.**
`playbooks/tenant-service-ca-verify.yml` sends a request that names a substrate host, a public name
and an address, and asks to be a CA and a client. It checks that none of that is in the certificate
that comes back, and then that eleven names are refused, among them a substrate service, the site's
zone, a wildcard and an address. It issues one certificate each run, for a name under a tenant that
does not exist, and deletes the key.

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
