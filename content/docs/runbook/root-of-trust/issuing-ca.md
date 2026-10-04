---
title: "Issuing CA"
weight: 2
---

# Issuing CA

A site's certificates are issued by two **issuing CAs** under its Site CA, each signed in this
ceremony:

| Issuing CA | Its key lives in | Issues |
|---|---|---|
| Deevnet Mobile Substrate CA | site automation, which signs on the control node | every substrate certificate: hosts, appliances, service VMs and their services, the secret store's own listener |
| Deevnet Mobile Tenant Device CA | the secret store, behind the Deevnet API | tenant devices' client certificates (mTLS) |

Each is valid for five years. **Its key is generated where it lives,** and only its signing request
comes to the ceremony. The Site CA's holder never sees an issuing CA's key, and the issuing CA's
system never sees the Site CA's.

The ceremony moves the request out and the certificate back on the **transfer media**, and three
commands do the mechanics and the checking. The decision to sign stays yours, and the Site CA's key
stays on its **key media**, which never crosses to the online side.

```
online (control node)                    transfer media                    offline machine
─────────────────────                    ──────────────                    ───────────────
1. deevnet-pki-transfer.sh prepare  ──►  to-offline/  request,        ──►  2. deevnet-pki-sign.sh
                                             certificates, MANIFEST           (on the ceremony image)
                                                                               + the Site CA key
                                                                               (its own key media)
3. deevnet-pki-transfer.sh accept   ◄──  to-online/   certificate,    ◄──
                                             MANIFEST
```

The online commands are in `ansible-collection-deevnet.mgmt/scripts/pki/`; the offline one is
installed on the [ceremony image](/docs/runbook/root-of-trust/ceremony/#the-ceremony-machine), so the
transfer media carries data only, never code that runs offline. Every step fails, and changes nothing,
if it finds a private key anywhere on the transfer media, by file name or by content.

## 1. Prepare (online)

**On the control node, prepare the transfer media with the request and the chain.** Automation first makes the issuing CA's key and request where the key will live; the substrate
runbook has that procedure for each CA. Then, on the control node, mount the transfer drive (plain
FAT32, labeled `TRANSFER`):

```bash
sudo mkdir -p /mnt/transfer && sudo mount -o uid=$(id -u),gid=$(id -g) LABEL=TRANSFER /mnt/transfer
```

```bash
cd ansible-collection-deevnet.mgmt/scripts/pki
./deevnet-pki-transfer.sh prepare /mnt/transfer \
  --site mobile --ca substrate --csr /path/to/deevnet-mobile-substrate-ca.csr
```

It checks the request:
- the request's signature verifies;
- the subject is exactly `O=Deevnet, OU=Mobile Site, CN=Deevnet Mobile Substrate CA`;
- the key is RSA 3072 or larger.

Then it empties `deevnet-transfer/` on the media and writes `to-offline/` with:
- the request;
- the Root CA and Site CA certificates;
- a `MANIFEST` of SHA-256 hashes.

On a [Fedora live USB](/docs/runbook/root-of-trust/ceremony/#without-a-pi-a-fedora-live-usb), add
`--with-tools`: it also writes the signing profile and `deevnet-pki-sign.sh`, under the same manifest.

It prints the manifest's own hash and the request's public-key hash. **Write both in the paper
record.**

`--ca tenant-device` does the same for the Tenant Device CA.

## 2. Sign (offline)

**On the offline machine, check the request and sign it with the Site CA.** On the [prepared](/docs/runbook/root-of-trust/ceremony/#run-the-ceremony) offline machine, with the transfer media
and the **Site CA's key media**, opened:

```bash
sudo deevnet-pki-media.sh keys open                  # the key drive's passphrase; /mnt/keys
sudo deevnet-pki-media.sh transfer mount             # /mnt/transfer
deevnet-pki-sign.sh /mnt/transfer --site-key /mnt/keys/deevnet-mobile-site-ca.key
```

On a Fedora live USB, run the copy that came on the transfer media:
`bash /mnt/transfer/deevnet-transfer/to-offline/deevnet-pki-sign.sh /mnt/transfer --site-key …`.

It first shows the clock and asks you to confirm it, because the certificate's five years start
there; it refuses a date earlier than the ceremony image was built. Then it refuses to go on unless:
- every network interface is down;
- the Site CA's key is on its own media, not the transfer media;
- the transfer media holds no private key;
- the manifest matches its files;
- the key given is the Site CA's;
- the request's signature verifies.

Then it shows:
- the manifest's hash: **compare it with the paper record**;
- the request's subject and public-key hash;
- the Site CA that will sign;
- what will be applied: five years, `CA:TRUE pathlen:0`, from the profile only.

It asks for the Site CA key's passphrase once, then asks you to **type the CA's name** to sign. That
is the trust decision, and nothing is signed without it.

After signing it checks the certificate chains to the root with `pathlen:0`, and that it carries the
request's key. It writes **only** the certificate and a return `MANIFEST` to `to-online/`, and prints
the certificate's SHA-256 fingerprint. **Write it in the paper record.** Then close both drives and
shut down (`sudo deevnet-pki-media.sh keys close; sudo deevnet-pki-media.sh transfer umount; sudo poweroff`).

## 3. Accept (online)

**Back on the control node, verify the certificate before automation installs it:**

```bash
./deevnet-pki-transfer.sh accept /mnt/transfer \
  --csr /path/to/deevnet-mobile-substrate-ca.csr --out /path/for/installation
```

It checks:
- the return manifest matches its files;
- the certificate is for the original request's key and has its subject;
- it chains to the Deevnet Root CA through the Site CA, using the **inventory's** copies of both,
  never the copies on the media;
- it is an issuing CA, `pathlen:0`.

It prints the fingerprint; **compare it with the paper record**. Only then does it copy the
certificate to `--out`, for automation to install beside the key it already holds.

## Rotation

**Rotate an issuing CA before its five years run out.** Run the ceremony again with a new request before the five years run out. The old CA's certificates
stay valid until they expire, and clients trust both, because they trust the root.
