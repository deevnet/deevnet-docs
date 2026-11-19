---
title: "Choose Its Certificates"
weight: 7
---

# Choose Its Certificates

**Every backend starts on its own CA, made at its first boot, and can move to one of two others.**
While your tenant is at the Mobile Factory, it can take a certificate from Deevnet for your
tenant's own names, and become a **Deevnet backend** (a "Deevnet Pi" in
[ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/)). When you
leave Deevnet, it can move to a PKI of your own. Both are the same `deevnet-kit` commands on every
medium.

## Take a certificate from Deevnet

**A Deevnet backend serves a certificate from Deevnet's Tenant Service CA for your tenant's names,
and trusts the Deevnet Root** (ADR-0041 §2). This is how a backend runs at a Deevnet production
site. The key is made on the backend and never leaves it; only a signing request travels. Signing
it is a Terraform apply, so it is done while you have the tenant at the Mobile Factory.

1. **On the backend, make the key and the request:**

   ```bash
   sudo deevnet-kit cert request
   ```

   It prints the request and keeps it in `/etc/deevnet-kit/tls/server.csr`; the new key waits beside
   the certificate it will replace.
2. **Have it signed, in your tenant's Terraform.** A
   [`deevnet_certificate`](/docs/runbook/tenant/services/certificates/) with that request,
   `name = "mqtt"`, `names = ["logs", "grafana", "metrics", "ntfy", "s3"]` plus any of your app's
   own, and `sites` listing where the backend runs or is headed, such as `["mobile", "home"]`.
   Apply, and copy `fullchain_pem` and `deevnet-root-ca.pem` to the backend.
3. **Install it:**

   ```bash
   sudo deevnet-kit cert install fullchain.pem deevnet-root-ca.pem
   ```

   It checks the certificate is for the waiting key, chains to the root given, and names `mqtt`,
   `logs`, `grafana`, `metrics`, `ntfy` and `s3` under `<tenant>.deevnet.net`, before changing
   anything. Then it installs it, makes the root what every service on the backend trusts, keeps
   the backend's own CA as `/etc/deevnet-kit/tls/card-ca.pem`, and restarts the broker, the log
   store, Grafana, the bridge and ntfy. Then it writes Grafana's data sources again, for the new
   names.

**The backend then answers to `mqtt.<tenant>.deevnet.net`, `logs.<tenant>.deevnet.net` and
`grafana.<tenant>.deevnet.net`.** Its own services dial those names, which it maps to itself in
`/etc/hosts`. Devices and computers dial them too, so the network the backend runs on has to
answer them with its address: at a Deevnet production site, its DNS does
([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) §1).
Run `sudo deevnet-kit export ~/deevnet-kit` again: `kit.env` names those hosts, and the CA is
`deevnet-root-ca.pem`. Devices then trust the Deevnet Root, as they do on Deevnet.

**It is renewed within the year, with the same key or a new one.** From sixty days before it
expires, a plan of your tenant shows the certificate renewing for the same key. Apply, copy the new
`fullchain_pem` to the backend, and run `sudo deevnet-kit cert install fullchain.pem
deevnet-root-ca.pem` with the root the backend already trusts: it replaces the certificate and
keeps the key. For a new key, run `cert request` first and replace the certificate's request with
the new one, then apply and install.

## A PKI of your own

**When you leave Deevnet, the backend can move to a PKI of your own, with its devices connected
throughout** (ADR-0041 §3, §4). It is two tiers: your root, on an encrypted USB stick you keep
apart from the backend, and an issuing CA on the backend, which signs the backend's certificate and
your devices'. Deevnet holds nothing of it and trusts none of it. A backend that never became a
Deevnet backend takes the same path.

**You need a USB stick you can erase, and two passphrases.** One unlocks the stick, the other
protects your root's key on it. Write both down, with the root's fingerprint the tool prints: they
are the only way into your root.

1. **Make your root and the backend's issuing CA.** With the stick unplugged:

   ```bash
   sudo deevnet-kit pki init --org "Your Name Home"
   ```

   It asks for the stick, offers to erase and encrypt it, makes your root on it and the issuing CA
   on the backend, and closes the stick. Nothing the backend serves changes. `--domain
   example.com` lets your CA sign names in a domain of yours as well; `.local` names, `localhost`
   and private addresses it always may.
2. **Give every device and computer both roots.** `sudo deevnet-kit export ~/deevnet-kit` now writes
   `trust-bundle.pem`, the root they trust now and yours, and `kit.env` names it. Put it on each
   device in place of the CA file it has.
3. **Switch the backend.**

   ```bash
   sudo deevnet-kit pki switch
   ```

   The backend then serves a certificate from your CA, and everything on it trusts your root.
   Devices holding the bundle reconnect as the broker restarts, with nothing changed on them. A
   Deevnet backend keeps its names, `mqtt.<tenant>.deevnet.net` and the rest: your CA may sign names
   under `<tenant>.deevnet.net`, so a device verifies the same name before and after.
4. **Once every device holds the bundle, take the Deevnet Root off them.** `export` now writes
   `owner-root-ca.pem` alone: put it on each device in place of the bundle.

**A device's own certificate comes from the backend.** `sudo deevnet-kit pki enroll DEVICE --out
DIR` makes its key and certificate in `DIR`; with `--csr FILE`, it signs the request a device made
itself. The backend renews its own certificate with `sudo deevnet-kit regen-certs`, with no stick.

**A lost or broken backend costs the issuing CA, never your root.** Bring up a new one, a fresh
card or VM, then with the stick:

```bash
sudo deevnet-kit pki issuing --org "Your Name Home" --domain <tenant>.deevnet.net
sudo deevnet-kit pki switch
```

`--domain <tenant>.deevnet.net` only for a backend that was a Deevnet backend. Recreate your broker
accounts with their passwords
([Move your tenant](/docs/runbook/tenant/take-it-home/move-your-tenant/#recreate-your-broker-accounts)),
and every device connects to the new backend unchanged: it trusts the same root.
