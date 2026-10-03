---
title: "Root CA"
weight: 2
---

# Root CA

The Deevnet Root CA is made **once**, for the whole organization, and every site's CA is signed by it.
It is valid for twenty years and its key is RSA 4096.

On the [prepared](/docs/runbook/root-of-trust/preparing/) offline machine, in `/dev/shm/pki`, with
`deevnet-pki.cnf` beside you, and the key media and transfer media
[prepared](/docs/runbook/root-of-trust/preparing/#prepare-new-media). **Check `date -u` first:** the
root's twenty years start from the clock.

The key is made in memory (`/dev/shm/pki`), copied onto the encrypted key drives, and gone at
shutdown.

## 1. Generate the key

**The root's key is encrypted with a passphrase as it is made:**

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -aes-256-cbc -out deevnet-root-ca.key
```

It asks for the passphrase twice. The file is encrypted with it; without the passphrase it is
useless, and without the file the passphrase is.

## 2. Self-sign

**The root signs its own certificate, from the profile's `v3_root` extensions:**

```bash
openssl req -x509 -new -config deevnet-pki.cnf -key deevnet-root-ca.key \
  -extensions v3_root -days 7305 -sha256 \
  -set_serial 0x$(openssl rand -hex 16) \
  -out deevnet-root-ca.pem
```

## 3. Check it

**Check the subject, the lifetime and the extensions before the key is stored:**

```bash
openssl x509 -in deevnet-root-ca.pem -noout -subject -issuer -enddate -ext basicConstraints,keyUsage
openssl x509 -in deevnet-root-ca.pem -noout -fingerprint -sha256
```

- Subject and issuer both read `O = Deevnet, OU = Deevnet PKI, CN = Deevnet Root CA`.
- It ends twenty years from today.
- `CA:TRUE, pathlen:2`, and `Certificate Sign, CRL Sign`.

## 4. Store it

**The key and certificate go on each key drive, and the certificate alone on the transfer drive:**

```bash
sudo deevnet-pki-media keys open primary          # the drive's passphrase
cp deevnet-root-ca.key deevnet-root-ca.pem /mnt/keys/
openssl pkey -in /mnt/keys/deevnet-root-ca.key -noout   # the key's passphrase; prints nothing
sudo deevnet-pki-media keys close
# the backup drive the same way (keys open backup), now or later

sudo deevnet-pki-media transfer mount
cp deevnet-root-ca.pem /mnt/transfer/
```

- The key goes on the key drives and nowhere else.
- The certificate is public. The key drive keeps a copy for the Site CA's signing.
- The fingerprint, the date and "Deevnet Root CA, 20 years" go in the paper record.

Making the Site CA next, in the same session? Leave everything open and go on. Otherwise
[finish up](/docs/runbook/root-of-trust/preparing/#finishing-up).

## Hand off to automation

**Only the root's certificate is handed to automation.** The certificate, never the key, goes into the inventory at `pki/deevnet-root-ca.pem`, through a pull
request like any other inventory change. From there automation installs it as the trust anchor
everywhere.

Next: a [Site CA](/docs/runbook/root-of-trust/site-ca/) for each site.
