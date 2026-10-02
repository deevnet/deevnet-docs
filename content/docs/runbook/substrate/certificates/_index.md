---
title: "Certificates"
weight: 6
bookCollapseSection: true
---

# Certificates

Everything the site serves over TLS chains to one root, `CN=Deevnet mobile root CA`, kept offline
in the inventory vault
([ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/)). Two
intermediates sit under it and sign every certificate in service. Certificates last a year and are
laid down by the roles that build each host. `certs.yml` renews them all, and nothing renews them on
a clock.

## The hierarchy

| CA | Where its key is | Signs | Valid to |
|---|---|---|---|
| `Deevnet mobile root CA` | the inventory vault, `vault_site_root_ca_key` | the two intermediates, nothing else | 2046-10-02 |
| `Deevnet mobile intermediate CA` | inside OpenBao, generated there and never exported | the Platform services and the Omada controller (`pki/issue/platform`) | 2031-10-02 |
| `Deevnet mobile bootstrap CA` | the inventory vault, `vault_site_bootstrap_ca_key` | the core router and the hypervisors, on the control node | 2031-10-02 |

The bootstrap intermediate exists because the core router and the hypervisors come up before
OpenBao, and OpenBao's VM is built through them. A certificate only OpenBao could issue would make a
from-scratch rebuild wait on itself.

Both certificates are public and live in the inventory repository at `pki/mobile/`, outside the
inventory directory, because Ansible parses every file in there as inventory. The root's SHA-256
fingerprint is `68:D5:C9:8E:3D:2E:B2:DF:B6:1B:99:E4:F3:4D:F9:D3:B4:65:C3:66:34:97:30:97:36:B7:7B:60:C4:15:2C:6B`.

## What each certificate names

Names come from the inventory, never a hand list. For a host, `site_cert_dns_names` is its A record
plus every CNAME in `env.interfaces.<if>.dns.cnames` (the data the router's DNS publishes), and
`site_cert_ip_sans` is every interface address. A new alias reaches the certificate the next time it
is issued. Some certificates carry more:

| Certificate | Also names | Why |
|---|---|---|
| Core router | every VLAN gateway address | clients dial it from whichever segment they sit on (the Deevnet API on Platform) |
| Omada controller | `localhost`, `127.0.0.1` | the controller's own playbooks dial it that way |
| Deevnet API, state store | `127.0.0.1` | their roles' health checks |

## Who trusts the root

| Where | How |
|---|---|
| The Builder, the hypervisors, every management-plane VM | the OS trust store (`deevnet.builder.site_trust`) |
| Fedora VM templates | baked in by the image factory |
| Each service's own TLS directory | `deevnet-mobile-root-ca.pem`, beside its certificate |
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
- [Rotating](rotating/): a new intermediate, or a new root.
- [Troubleshooting](troubleshooting/): when a certificate is served but not trusted.
