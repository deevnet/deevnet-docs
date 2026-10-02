---
title: "Trusting the Root"
weight: 5
---

# Trusting the Root

Everything the site serves over TLS by name chains to one root, `deevnet-mobile-root-ca.pem`. Trust
it once on your computer and browsers and command-line tools verify the Deevnet API, the platform
services, Proxmox, the core router and the Omada controller without flags or warnings.

Check its SHA-256 fingerprint before you trust it:
`68:D5:C9:8E:3D:2E:B2:DF:B6:1B:99:E4:F3:4D:F9:D3:B4:65:C3:66:34:97:30:97:36:B7:7B:60:C4:15:2C:6B`.

```bash
curl -fsSLk -O https://downloads.mobile.deevnet.net:8443/deevnet-mobile-root-ca.pem
openssl x509 -in deevnet-mobile-root-ca.pem -noout -fingerprint -sha256
```

The first fetch skips verification (`-k`) because you do not trust the root yet. The fingerprint
check is what makes it safe.

## macOS

Into the System keychain, trusted as a root (`security(1)`, `add-trusted-cert`):

```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain deevnet-mobile-root-ca.pem
```

Safari and Chrome read the System keychain. Firefox keeps a certificate store of its own; check
Mozilla's current guidance before relying on it for the site.

## Fedora

```bash
sudo cp deevnet-mobile-root-ca.pem /etc/pki/ca-trust/source/anchors/ && sudo update-ca-trust extract
```

## Check it

```bash
curl -fsS https://api.mobile.deevnet.net:8080/version
```

It answers with no `--cacert` once the root is trusted. Open the appliances by name, for example
`https://pve.mobile.deevnet.net:8006/` or `https://omada.mobile.deevnet.net:8043/`, not through the
`localhost` tunnel ([Operator Access](/docs/runbook/substrate/network/operator-access/)): a
certificate names the service, not `localhost`.

Substrate hosts do not need this step: the build installs the root in their trust stores.
