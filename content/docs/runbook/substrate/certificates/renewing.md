---
title: "Renewing"
weight: 1
---

# Renewing

`certs.yml` in `ansible-collection-deevnet.mgmt` lays down every certificate and trust anchor on the
site, and is how certificates are renewed: re-run it. Nothing renews a certificate on a timer, so a
certificate on a host nobody re-applies will expire (risk register R-12).

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/certs.yml                 # everything
ansible-playbook playbooks/certs.yml --tags omada    # one play: trust, hypervisors, router, openbao, omada
ansible-playbook playbooks/certs.yml --limit dv02obs001v01
```

It needs the inventory's vaults decrypted, and `deevnet.builder` and `deevnet.net` published
(`make publish` in each), because the trust, hypervisor and router plays are theirs.

## What a run checks

Every certificate is reissued only when one of these holds:

- it is missing;
- it has fewer than 60 days left;
- it no longer chains to the site root (an OpenBao that was rebuilt, or a re-root);
- for the hypervisors, the names it carries differ from the inventory's.

Otherwise the run changes nothing. A run on a healthy site is `changed=0` on every host.

## What it does not do

**It does not change a service's configuration.** `certs.yml` renews certificates that services
already name. A first build, or a change to which files a service reads, goes through that
service's own `site.yml` play.

**The core router's GUI selection is manual the first time.** After that, renewal replaces the
certificate the GUI already uses. See [Core Router](/docs/runbook/substrate/certificates/core-router/).

## When to run it

At least every ten months, and after anything that might change what a certificate names: a new
CNAME, a new address, a rebuilt OpenBao. The intermediates and the root are not renewed by it; see
[Rotating](/docs/runbook/substrate/certificates/rotating/).
