---
title: "Site CA"
weight: 3
---

# Site CA

Each site (mobile, home, …) has its own Site CA, signed by the Deevnet Root CA. It signs that site's
issuing CAs and nothing else. It is valid for ten years and its key is RSA 3072. Its key is offline
like the root's, held by the same person.

The site's name is its title in the [naming standard](/docs/standards/naming/): `Mobile`, `Home`.
Below, `SITE=Mobile` and `site=mobile`.

On the [prepared](/docs/runbook/root-of-trust/preparing/) offline machine, in `/dev/shm/pki` with
`deevnet-pki.cnf`. **Check `date -u` first:** the Site CA's ten years start from the clock.

**On the `pi-pki` image, `./deevnet-pki-ceremony` runs this page step by step:** path 2 for a Site
CA under the root already on the key drive. Path 1 makes the root first.

The root signs it, so the key drive that holds the root is open:

```bash
sudo deevnet-pki-media keys open primary          # if it is not open already
sudo deevnet-pki-media transfer mount             # likewise
```

## 1. Generate the key and request

**The Site CA's key is encrypted as it is made, and its request names the site:**

```bash
SITE=Mobile; site=mobile
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -aes-256-cbc \
  -out deevnet-$site-site-ca.key
openssl req -new -key deevnet-$site-site-ca.key \
  -subj "/O=Deevnet/OU=$SITE Site/CN=Deevnet $SITE Site CA" \
  -out deevnet-$site-site-ca.csr
```

## 2. Sign with the root

**The root signs the request with the profile's `v3_site` extensions:**

```bash
openssl x509 -req -in deevnet-$site-site-ca.csr \
  -CA /mnt/keys/deevnet-root-ca.pem -CAkey /mnt/keys/deevnet-root-ca.key \
  -extfile deevnet-pki.cnf -extensions v3_site -days 3653 -sha256 \
  -set_serial 0x$(openssl rand -hex 16) \
  -out deevnet-$site-site-ca.pem
```

It asks for the root key's passphrase. The extensions come only from the profile, never from the
request.

## 3. Check the chain

**Check that the Site CA chains to the root before the key is stored:**

```bash
openssl x509 -in deevnet-$site-site-ca.pem -noout -subject -issuer -enddate -ext basicConstraints
openssl verify -CAfile /mnt/keys/deevnet-root-ca.pem deevnet-$site-site-ca.pem
openssl x509 -in deevnet-$site-site-ca.pem -noout -fingerprint -sha256
```

- Subject: `O = Deevnet, OU = Mobile Site, CN = Deevnet Mobile Site CA`. Issuer: the root.
- `CA:TRUE, pathlen:1`, ten years.
- `verify` answers `OK`.

## 4. Store it

**The key and certificate go on each key drive, and the certificate alone on the transfer drive:**

```bash
cp deevnet-$site-site-ca.key deevnet-$site-site-ca.pem /mnt/keys/
openssl pkey -in /mnt/keys/deevnet-$site-site-ca.key -noout   # prints nothing
cp deevnet-$site-site-ca.pem /mnt/transfer/
sudo deevnet-pki-media keys close
# the backup drive the same way (keys open backup), now or later
```

- The `.csr` can be left: `/dev/shm/pki` is gone at shutdown.
- The certificate goes, by pull request, into the inventory at `pki/$site/deevnet-$site-site-ca.pem`.
- The fingerprint goes in the paper record.

Then [finish up](/docs/runbook/root-of-trust/preparing/#finishing-up). On the Builder, mount the
transfer drive (`sudo mount LABEL=TRANSFER /mnt/transfer`) and take both certificates from it.

Next: the site's [issuing CAs](/docs/runbook/root-of-trust/issuing-ca/).
