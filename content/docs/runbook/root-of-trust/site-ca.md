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
`deevnet-pki.cnf`, and the **root's key media** mounted. **Check `date -u` first:** the Site CA's ten
years start from the clock.

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
  -CA deevnet-root-ca.pem -CAkey /path/to/key-media/deevnet-root-ca.key \
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
openssl verify -CAfile deevnet-root-ca.pem deevnet-$site-site-ca.pem
openssl x509 -in deevnet-$site-site-ca.pem -noout -fingerprint -sha256
```

- Subject: `O = Deevnet, OU = Mobile Site, CN = Deevnet Mobile Site CA`. Issuer: the root.
- `CA:TRUE, pathlen:1`, ten years.
- `verify` answers `OK`.

## 4. Store it

**The key goes on both key media, and the certificate into the inventory:**

- `deevnet-$site-site-ca.key` goes to both key media. The `.csr` can be deleted.
- `deevnet-$site-site-ca.pem` goes to the transfer media and, by pull request, into the inventory at
  `pki/$site/deevnet-$site-site-ca.pem`.
- The fingerprint goes in the paper record.

Next: the site's [issuing CAs](/docs/runbook/root-of-trust/issuing-ca/).
