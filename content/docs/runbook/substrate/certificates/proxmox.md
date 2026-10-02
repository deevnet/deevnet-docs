---
title: "Proxmox"
weight: 2
---

# Proxmox

Each hypervisor's web UI and API (`:8006`) serve a certificate signed by the bootstrap intermediate,
installed by `deevnet.builder.proxmox_node_cert` with Proxmox's own command:

```bash
pvenode cert set <chain.pem> <key.pem> --force 1 --restart 1
```

`pvenode(1)` writes `/etc/pve/local/pveproxy-ssl.pem` and `.key`. It refuses a key that does not
match, restoring the previous files, and never touches the node's own `pve-ssl.pem`, which pveproxy
falls back to when no custom certificate is present. `--restart 1` restarts pveproxy, which serves
the new certificate only after a restart. The node fingerprint changes with the certificate; nothing
on the site pins it, and the nodes are not clustered.

## Install or renew

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/certs.yml --tags hypervisors --limit dv02hyp002p02
```

The builder collection's `site.yml` runs the same role in the hypervisors play (`--tags certs`).

**Verify** from the Builder, which trusts the root:

```bash
curl -fsS -o /dev/null https://pve2.mobile.deevnet.net:8006/ && echo ok
openssl s_client -connect 10.20.99.22:8006 -showcerts -verify_ip 10.20.99.22 -verify_return_error \
  -CAfile /srv/dvnt/ansible-inventory-deevnet/pki/mobile/deevnet-mobile-root-ca.pem </dev/null
```

Two certificates (the leaf, then `Deevnet mobile bootstrap CA`) and `Verify return code: 0 (ok)`.

## Back it out

On the node, as root:

```bash
pvenode cert delete 1
```

pveproxy goes straight back to the node's own certificate. Set `site_verify_proxmox: false` in the
inventory first, or every client that verifies stops reaching the node.
