---
title: "Core Router"
weight: 3
---

# Core Router

The core router's web GUI and API (`:443`, one server) serve a certificate signed by the Substrate
CA. Ansible signs it on the control node and imports it, with the Deevnet Root CA, the Site CA and
the Substrate CA, over the documented Trust API (`deevnet.net.opnsense_cert`). **OPNsense has
no API for which certificate the web GUI serves**, so choosing it is a manual step, made once.

The certificate's description in the router is `Deevnet site certificate (dv02cor002p01.mobile.deevnet.net)`.

## 1. Import the certificate with Ansible

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/opnsense-cert.yml
```

The role imports the three CAs if they are absent, root first so each links to its issuer, then the
certificate (the leaf alone: the GUI appends the chain from the CA it links on import). It checks every write's result,
because a rejected write can answer HTTP 200, and reads the certificate back. It ends by checking
what the GUI serves, and until the next step is done it prints:

```text
MANUAL STEP: in the router GUI, System > Settings > Administration > SSL Certificate, choose
"Deevnet site certificate (dv02cor002p01.mobile.deevnet.net)" and Save (the GUI restarts).
```

Nothing the GUI serves has changed yet.

## 2. Choose the certificate in the GUI (the manual step)

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
    -CAfile /srv/dvnt/ansible-inventory-deevnet/pki/deevnet-root-ca.pem -no-CApath -no-CAstore </dev/null | grep 'Verify return'
done
```

Then set `site_verify_opnsense: true` in `group_vars/all`, merge it, and redeploy the Deevnet API
(`site.yml --skip-tags vms --limit dv02prv001v01`). The `opnsense_*` roles and the API verify from
then on; on this site they have since CHG-0033.

## Renewal replaces the certificate the GUI already uses

`certs.yml` and `opnsense.yml` run the same role. When the certificate is due, or is linked to any
CA other than today's Substrate CA (a re-root or a rotation), the role replaces the payload of the
certificate the GUI already uses (`trust/cert/set`), so the GUI choice survives. Then restart the GUI
from the console or over SSH (`configctl webgui restart`) to serve it.

The Trust API accepts the in-place replacement: CHG-0033 replaced the certificate this way and the
role's read-back confirmed it was linked to the new Substrate CA. After a replacement, a browser can
keep showing the old certificate from a cached connection; a new window shows the new one.

## Back out to the router's own certificate

**Back out from the GUI:** choose `Web GUI TLS certificate` (the router's own) under SSL Certificate, and Save.

**If the GUI does not come back, back out over SSH or the console**, as root:

```bash
configctl webgui restart renew
```

This generates a fresh self-signed certificate and points the GUI at it. That is read from
OPNsense's source (`webgui.inc`, `webgui_create_selfsigned`) and has not been run here. Set
`site_verify_opnsense: false` before any client needs the API again.

The imported CAs and certificate can stay; one that is in use cannot be deleted. CAs listed in
`opnsense_cert_retired_cas` are deleted by the role once the GUI serves the site certificate.
