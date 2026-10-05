---
title: "Trusting the Root"
weight: 5
---

# Trusting the Root

Everything the site serves over TLS by name chains to one root, the Deevnet Root CA,
`deevnet-root-ca.pem`. Trust it once on your computer and browsers and command-line tools verify the
Deevnet API, the platform services, Proxmox, the core router and the Omada controller without flags
or warnings.

Check its SHA-256 fingerprint before you trust it:
`F6:8A:BD:B3:1E:A5:6D:0A:88:1F:31:28:56:8A:4C:14:B0:3A:3F:5C:3F:38:CC:F1:7C:C4:F0:09:8B:EB:94:52`.

```bash
curl -fsSLk -O https://downloads.mobile.deevnet.net:8443/deevnet-root-ca.pem
openssl x509 -in deevnet-root-ca.pem -noout -fingerprint -sha256
```

The first fetch skips verification (`-k`) because you do not trust the root yet. The fingerprint
check is what makes it safe.

## Trust the root on macOS

Into the System keychain, trusted as a root (`security(1)`, `add-trusted-cert`):

```bash
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain deevnet-root-ca.pem
```

Safari and Chrome read the System keychain. Firefox keeps a certificate store of its own; check
Mozilla's current guidance before relying on it for the site.

## Trust the root on Windows

Download it as a `.crt` (`http://artifacts.mobile.deevnet.net/keys/pki/deevnet-root-ca.crt`, or the
`.pem` above renamed), check its fingerprint, then put it **in the Trusted Root store, chosen
explicitly**:

```powershell
certutil -dump .\deevnet-root-ca.crt | findstr /i sha256      # f68abdb31ea5...8beb9452
certutil -addstore -f Root .\deevnet-root-ca.crt               # administrator PowerShell
```

Or double-click it: **Install Certificate… > Local Machine > Place all certificates in the following
store > Trusted Root Certification Authorities**. Never let the wizard choose the store
automatically: it can file a root under *Intermediate Certification Authorities*, where Windows
never treats it as a trust anchor. That is how the ADR-0030 root was found on the operator's computer
after CHG-0033: present, and never trusted.

Check what landed where:

```powershell
Get-ChildItem -Recurse Cert:\ | Where-Object { $_.Subject -like '*Deevnet*' } |
  Select-Object PSParentPath, Subject, Thumbprint | Format-List
```

`CN=Deevnet Root CA` must appear under `...\Root`; its SHA-1 thumbprint is
`14E9FB1A79CE27F92B66F458E3D48448C68D0AC5`. Copies under `...\CA` are Windows caching chains it was
sent, and are harmless.

## Trust the root on Fedora

```bash
sudo cp deevnet-root-ca.pem /etc/pki/ca-trust/source/anchors/ && sudo update-ca-trust extract
```

## Check the root is trusted

```bash
curl -fsS https://api.mobile.deevnet.net:8080/version
```

It answers with no `--cacert` once the root is trusted. Open the appliances by name, for example
`https://pve.mobile.deevnet.net:8006/` or `https://omada.mobile.deevnet.net:8043/`, not through the
`localhost` tunnel ([Operator Access](/docs/runbook/substrate/network/operator-access/)): a
certificate names the service, not `localhost`.

Substrate hosts do not need this step: the build installs the root in their trust stores.
