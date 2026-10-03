---
title: "Root CA"
weight: 2
---

# Root CA

The Deevnet Root CA is made **once**, for the whole organization, and every site's CA is signed by it.
It is valid for twenty years and its key is RSA 4096.

On the [prepared](/docs/runbook/root-of-trust/preparing/) offline machine, in `/dev/shm/pki`, with
`deevnet-pki.cnf` beside you. **Check `date -u` first:** the root's twenty years start from the
clock.

## 1. Generate the root's passphrase-encrypted key

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -aes-256-cbc -out deevnet-root-ca.key
```

It asks for the passphrase twice. The file is encrypted with it; without the passphrase it is
useless, and without the file the passphrase is.

## 2. Self-sign the root's certificate

```bash
openssl req -x509 -new -config deevnet-pki.cnf -key deevnet-root-ca.key \
  -extensions v3_root -days 7305 -sha256 \
  -set_serial 0x$(openssl rand -hex 16) \
  -out deevnet-root-ca.pem
```

## 3. Check the root's subject, lifetime and extensions

```bash
openssl x509 -in deevnet-root-ca.pem -noout -subject -issuer -enddate -ext basicConstraints,keyUsage
openssl x509 -in deevnet-root-ca.pem -noout -fingerprint -sha256
```

- Subject and issuer both read `O = Deevnet, OU = Deevnet PKI, CN = Deevnet Root CA`.
- It ends twenty years from today.
- `CA:TRUE, pathlen:2`, and `Certificate Sign, CRL Sign`.

## 4. Put the key on both key media and the certificate on the transfer media

- `deevnet-root-ca.key` goes to **both** key media, and nowhere else.
- `deevnet-root-ca.pem` goes to the transfer media. It is public.
- The fingerprint, the date and "Deevnet Root CA, 20 years" go in the paper record.

Then [finish](/docs/runbook/root-of-trust/preparing/#finishing-up) and shut
down.

## Only the root's certificate is handed to automation

The certificate, never the key, goes into the inventory at `pki/deevnet-root-ca.pem`, through a pull
request like any other inventory change. From there automation installs it as the trust anchor
everywhere.

Next: a [Site CA](/docs/runbook/root-of-trust/site-ca/) for each site.
