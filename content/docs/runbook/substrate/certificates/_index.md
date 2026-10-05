---
title: "Certificates"
weight: 6
bookCollapseSection: true
---

# Certificates

Everything the site serves over TLS chains to the **Deevnet Root CA**, through the **Mobile Site
CA** and the **Mobile Substrate CA**
([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/)). The root and the Site CA are
kept offline ([Root of Trust](/docs/runbook/root-of-trust/)). The Substrate CA's key is in the
inventory vault, and it signs every substrate certificate on the control node, OpenBao's own
listener included. Certificates last a year and are laid down by the roles that build each host.
`certs.yml` renews them all, and nothing renews them on a clock.

## The chain

**Four CAs, two of them offline, sign everything on the site:**

| CA | Where its key is | Signs | Valid to |
|---|---|---|---|
| `Deevnet Root CA` | offline ([Root of Trust](/docs/runbook/root-of-trust/)) | Site CAs only | 2046-10-04 |
| `Deevnet Mobile Site CA` | offline | the mobile site's issuing CAs only | 2036-10-04 |
| `Deevnet Mobile Substrate CA` | the inventory vault, `vault_site_substrate_ca_key` | every substrate certificate, on the control node (`deevnet.builder.substrate_cert`) | 2031-10-04 |
| `Deevnet Mobile Tenant Device CA` | inside OpenBao, `pki-tenant-device`, never exported | tenant devices' client certificates (not yet issuing) | 2031-10-04 |

**Every substrate service serves its leaf, the Substrate CA and the Site CA,** so a client that holds
only the root can build the chain. Omada also sends the root, which its image wants in the chain.

**The Site CA is name-constrained** to `deevnet.net`, `localhost`, and private and loopback
addresses, so nothing under it can vouch for a public site.

The certificates are public, in the inventory repository: the root at `pki/deevnet-root-ca.pem`, and
the site's CAs in `pki/mobile/`, outside the inventory directory because Ansible parses every file in
there as inventory. The root's SHA-256 fingerprint is
`F6:8A:BD:B3:1E:A5:6D:0A:88:1F:31:28:56:8A:4C:14:B0:3A:3F:5C:3F:38:CC:F1:7C:C4:F0:09:8B:EB:94:52`.

## Every certificate's names come from the inventory

Names come from the inventory, never a hand list. For a host, `site_cert_dns_names` is its A record
plus every CNAME in `env.interfaces.<if>.dns.cnames` (the data the router's DNS publishes), and
`site_cert_ip_sans` is every interface address. A new alias reaches the certificate the next time it
is issued. Some certificates carry more:

| Certificate | Also names | Why |
|---|---|---|
| Core router | every VLAN gateway address | clients dial it from whichever segment they sit on (the Deevnet API on Platform) |
| Omada controller | `localhost`, `127.0.0.1` | the controller's own playbooks dial it that way |
| Deevnet API, state store | `127.0.0.1` | their roles' health checks |

## Where the root is trusted

| Where | How |
|---|---|
| The Builder, the hypervisors, every management-plane VM | the OS trust store (`deevnet.builder.site_trust`) |
| Fedora VM templates | baked in by the image factory |
| Each service's own TLS directory | `deevnet-root-ca.pem`, beside its certificate |
| Tenants | they download it once and pass it to each tool by file |
| Your computer | [by hand](trusting-the-root/) |

Clients of the three appliances verify only when the inventory says they can:
`site_verify_proxmox`, `site_verify_opnsense` and `site_verify_omada` in `group_vars/all`. The
Deevnet API's `*_INSECURE_TLS`, Ansible's `validate_certs`, Packer and the tenant fabric all follow
those switches.

## In this section

- [Renewing](renewing/): `certs.yml`, and what it checks.
- [Proxmox](proxmox/), [Core Router](core-router/), [Omada Controller](omada-controller/): how each
  appliance takes its certificate, and how to back it out.
- [Trusting the Root](trusting-the-root/): on your own computer.
- [Rotating](rotating/): a new issuing CA, Site CA or root.
- [Root of Trust](/docs/runbook/root-of-trust/): the offline ceremonies for the Deevnet Root CA and
  each Site CA ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/)).
- [Troubleshooting](troubleshooting/): when a certificate is served but not trusted.
