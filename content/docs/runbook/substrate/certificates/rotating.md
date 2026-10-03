---
title: "Rotating"
weight: 6
---

# Rotating

Certificates are renewed by [Renewing](/docs/runbook/substrate/certificates/renewing/). The CAs above them change only deliberately.

## Rotate the OpenBao intermediate with the openbao play

Valid five years. Rotate it before it expires, or after an OpenBao rebuild that lost its data (the
`openbao` role signs a new one then without being asked):

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/openbao.yml -e openbao_pki_rotate_intermediate=true
ansible-playbook playbooks/certs.yml
```

The new intermediate becomes OpenBao's default issuer. Certificates the old one signed still chain to
the root and stay in service until they are due, so `certs.yml` reissues nothing, and no client is
handed anything. The [OpenBao Drills](/docs/runbook/substrate/recovery/substrate-secrets-drills/)
rehearse exactly this.

## A new bootstrap intermediate is a deliberate, hand-made step

Valid five years, and its key is in the vault. A new one is signed by the root on the control node,
the same way `playbooks/site-root-ca.yml` signed the first. That playbook refuses to run on a site
that has a root, so a rotation is a deliberate, hand-made step. Once it is done,
`certs.yml --tags hypervisors,router` reissues the router's and the hypervisors' certificates.

## A new root means re-rooting everything

Valid to 2046-10-02. A new root is a re-root: every tenant, every embedded copy (`tenant-check.sh`,
`install-provider.sh`, `segment-check.sh`), the VM templates and every computer that trusts it take
the new one. [CHG-0031](/docs/changes/2026/0031-site-root-ca/) is the record of the last one.

Each site has its own root. If a second site is built, an offline organization root can cross-sign
each site root, so that one anchor trusts every site without re-rooting either
([ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/), open questions).
