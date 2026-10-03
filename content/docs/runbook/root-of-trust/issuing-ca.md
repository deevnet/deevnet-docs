---
title: "Issuing CA"
weight: 4
---

# Issuing CA

A site's certificates are issued by two **issuing CAs** under its Site CA, each signed in this
ceremony:

| Issuing CA | Its key lives in | Issues |
|---|---|---|
| Deevnet Mobile Substrate CA | the site's ansible-vault; automation signs on the control node | every substrate certificate: hosts, appliances, service VMs and their services, the secret store's own listener |
| Deevnet Mobile Tenant Device CA | the secret store, behind the Deevnet API | tenant devices' client certificates (mTLS) |

Each is valid for five years. **Its key is generated where it lives,** and only its signing request
comes to the ceremony. The holder of the Site CA never sees an issuing CA's key, and the issuing CA's
system never sees the Site CA's.

## 1. Automation makes the key and the request

This happens online, before the ceremony. The procedure is in the substrate runbook for each CA. The
result is a file on the transfer media:

- `deevnet-mobile-substrate-ca.csr`, with subject `O=Deevnet, OU=Mobile Site, CN=Deevnet Mobile Substrate CA`;
- or `deevnet-mobile-tenant-device-ca.csr`, with `CN=Deevnet Mobile Tenant Device CA`.

The subject in the request is what the certificate will carry; check it before you sign.

## 2. Sign it

On the [prepared](/docs/runbook/root-of-trust/preparing/) offline machine, with the **Site CA's key
media** mounted:

```bash
site=mobile; ca=substrate        # or: ca=tenant-device
openssl req -in deevnet-$site-$ca-ca.csr -noout -subject -verify
openssl x509 -req -in deevnet-$site-$ca-ca.csr \
  -CA deevnet-$site-site-ca.pem -CAkey /path/to/key-media/deevnet-$site-site-ca.key \
  -extfile deevnet-pki.cnf -extensions v3_issuing -days 1826 -sha256 \
  -set_serial 0x$(openssl rand -hex 16) \
  -out deevnet-$site-$ca-ca.pem
```

`-verify` checks the request was signed by the key it carries. The extensions, including
`pathlen:0`, come from the profile: whatever the request asked for is ignored.

## 3. Check it

```bash
cat deevnet-$site-site-ca.pem > chain.pem
openssl verify -CAfile deevnet-root-ca.pem -untrusted chain.pem deevnet-$site-$ca-ca.pem
openssl x509 -in deevnet-$site-$ca-ca.pem -noout -subject -issuer -enddate -ext basicConstraints
openssl x509 -in deevnet-$site-$ca-ca.pem -noout -fingerprint -sha256
```

`OK`; issuer `Deevnet Mobile Site CA`; `CA:TRUE, pathlen:0`; five years.

## 4. Hand it back

`deevnet-$site-$ca-ca.pem` goes to the transfer media, and from there to automation, which installs it
beside the key it already holds. Record the fingerprint and the date. There is no key to keep from
this ceremony.

## Rotating one

Run this ceremony again with a new request before the five years run out. The old CA's certificates
stay valid until they expire, and clients trust both, because they trust the root.
