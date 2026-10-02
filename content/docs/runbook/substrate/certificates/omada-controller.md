---
title: "Omada Controller"
weight: 4
---

# Omada Controller

The controller's web UI and Open API (`:8043`) and its portal (`:8843`) serve a certificate from
OpenBao's intermediate, through the container image's own mechanism. Its entrypoint builds the
keystore from two files in `/cert` on every start (`mbentley/omada-controller` README):

- `/cert/tls.crt`: **the full chain, root included**;
- `/cert/tls.key`.

The `omada_controller` role writes both into `/opt/omada-controller/cert` with `site_cert`, mounts
the directory at `/cert`, and restarts the controller when they change. It is on where
`omada_tls_enabled: true` (`group_vars/network_controllers`).

**Never install a certificate through the controller's UI or its Open API as well.** That stores it
in MongoDB, and the `/cert` mount stops working.

Adoption and inform (29810–29817) do not use this certificate. Port 8043 also serves device firmware
upgrades; an upgrade through it has not yet been run against the site certificate.

## Install or renew

```bash
cd ansible-collection-deevnet.mgmt
ansible-playbook playbooks/certs.yml --tags omada
```

A renewal restarts the controller, because the keystore is read only at start. Devices stay up
meanwhile.

**Verify:**

```bash
for p in 8043 8843; do
  openssl s_client -connect omada.mobile.deevnet.net:$p -showcerts -verify_return_error \
    -CAfile /srv/dvnt/ansible-inventory-deevnet/pki/mobile/deevnet-mobile-root-ca.pem </dev/null | grep 'Verify return'
done
```

Three certificates (leaf, intermediate, root) on each port. Then check every device is still
connected in the controller.

## Back it out

The first time the role ran, it kept the controller's own keystore as
`/opt/omada-controller/data/keystore/eap.keystore.pre-chg0032`.

1. Set `omada_tls_enabled: false` and `site_verify_omada: false`, and merge.
2. On `dv02nms001v01`, as root: copy `eap.keystore.pre-chg0032` back over `eap.keystore` (owner
   `omada`, UID 508). Without this step the site certificate stays in the keystore, because the
   entrypoint only overwrites it when both `/cert` files are present.
3. `ansible-playbook playbooks/site.yml --skip-tags vms --limit dv02nms001v01`, which recreates the
   controller without the mount.
