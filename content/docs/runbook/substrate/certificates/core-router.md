---
title: "Core Router"
weight: 3
---

# Core Router

The core router's web GUI and API (`:443`, one server) serve a certificate signed by the bootstrap
intermediate. Ansible signs it on the control node and imports it, with the site root and the
bootstrap intermediate, over the documented Trust API (`deevnet.net.opnsense_cert`). **OPNsense has
no API for which certificate the web GUI serves**, so choosing it is a manual step, made once.

The certificate's description in the router is `Deevnet site certificate (dv02cor002p01.mobile.deevnet.net)`.

## 1. Import

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/opnsense-cert.yml
```

The role imports the root and the intermediate if they are absent, then the certificate (the leaf
alone: the GUI appends the chain from the CA it links on import). It checks every write's result,
because a rejected write can answer HTTP 200, and reads the certificate back. It ends by checking
what the GUI serves, and until the next step is done it prints:

```text
MANUAL STEP: in the router GUI, System > Settings > Administration > SSL Certificate, choose
"Deevnet site certificate (dv02cor002p01.mobile.deevnet.net)" and Save (the GUI restarts).
```

Nothing the GUI serves has changed yet.

## 2. Choose it in the GUI

Keep an SSH session to the router open before you start; it is the way back if the GUI does not
return.

1. Open `https://10.20.99.1/` and log in.
2. **System > Settings > Administration**.
3. **SSL Certificate**: choose `Deevnet site certificate (dv02cor002p01.mobile.deevnet.net)`. The
   list shows only certificates with a private key.
4. **Save**. The page refuses a certificate without the serverAuth extended key usage; this one has
   it. The web GUI restarts after about three seconds ("The web GUI is reloading at the moment").
5. Reload the page. If your computer [trusts the root](/docs/runbook/substrate/certificates/trusting-the-root/), open it by name,
   `https://gateway.mobile.deevnet.net/`, and it loads with no warning.

Leave **HTTP Strict Transport Security** off on the same page until verification is proven: with it
on, a browser offers no way past a bad certificate.

## 3. Verify and turn verification on

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/opnsense-cert.yml     # now ends: "The web GUI serves the site certificate."
for ip in 10.20.99.1 10.20.25.1; do
  openssl s_client -connect $ip:443 -verify_ip $ip -verify_return_error \
    -CAfile /srv/dvnt/ansible-inventory-deevnet/pki/mobile/deevnet-mobile-root-ca.pem </dev/null | grep 'Verify return'
done
```

Then set `site_verify_opnsense: true` in `group_vars/all`, merge it, and redeploy the Deevnet API
(`site.yml --limit dv02prv001v01 --tags deevnet-api`). The `opnsense_*` roles and the API verify from
then on.

## Renewal

`certs.yml` and `opnsense.yml` run the same role. When the certificate is due, the role replaces the
payload of the certificate the GUI already uses (`trust/cert/set`), so the GUI choice survives. Then
restart the GUI from the console or over SSH (`configctl webgui restart`) to serve it.

The first renewal confirms that the Trust API accepts an in-place replacement: the role's read-back
fails if it did not. If it does not, import a new certificate and choose it in the GUI again, as
above.

## Back it out

**From the GUI:** choose `Web GUI TLS certificate` (the router's own) under SSL Certificate, and Save.

**If the GUI does not come back,** over SSH or the console, as root:

```bash
configctl webgui restart renew
```

This generates a fresh self-signed certificate and points the GUI at it. That is read from
OPNsense's source (`webgui.inc`, `webgui_create_selfsigned`) and has not been run here. Set
`site_verify_opnsense: false` before any client needs the API again.

The imported CAs and certificate can stay; one that is in use cannot be deleted.
