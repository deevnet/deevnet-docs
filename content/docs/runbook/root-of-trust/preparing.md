---
title: "Preparing"
weight: 1
---

# Preparing

Every ceremony runs on a machine with no network, so a key it touches can only leave on the media
you carry away.

## What you need

- **A live USB** of a current Fedora Workstation release. It has `openssl`, and nothing it does
  survives a reboot.
- **Two USB drives for the keys** (the *key media*), kept apart afterwards: the primary and the
  backup.
- **One USB drive for transfer** (the *transfer media*): it carries certificates and signing requests
  in and out, never a key.
- **The paper record**, a notebook or sheet, for fingerprints and dates.
- **The passphrase** for the key files, kept offline, under the holder's own control.

## Bring up the offline machine

1. Boot the live USB on any machine, ideally with its network cable unplugged and Wi-Fi switched
   off in hardware.
2. Turn networking off, and confirm it is off:

   ```bash
   nmcli networking off
   nmcli networking            # disabled
   ip -brief address           # only lo
   ```
3. Make a working directory in memory, which disappears at shutdown:

   ```bash
   mkdir -m 0700 /dev/shm/pki && cd /dev/shm/pki
   ```
4. Mount the key media and the transfer media. Copy in, from the transfer media, only what this
   ceremony needs: the profile below, and a signing request if you are signing one.

## The profile file

Every ceremony uses this file, `deevnet-pki.cnf`. Keep a copy on the transfer media. It holds the
root's name and every CA's extensions; the names below the root are given on the command line.

```ini
# Deevnet PKI - certificate profiles for the offline ceremonies (standards/certificates).
[ req ]
prompt             = no
distinguished_name = dn_root
string_mask        = utf8only

[ dn_root ]
O  = Deevnet
OU = Deevnet PKI
CN = Deevnet Root CA

[ v3_root ]
basicConstraints       = critical, CA:TRUE, pathlen:2
keyUsage               = critical, keyCertSign, cRLSign
subjectKeyIdentifier   = hash

[ v3_site ]
basicConstraints       = critical, CA:TRUE, pathlen:1
keyUsage               = critical, keyCertSign, cRLSign
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always

[ v3_issuing ]
basicConstraints       = critical, CA:TRUE, pathlen:0
keyUsage               = critical, keyCertSign, cRLSign
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always
```

The path lengths are what keep each layer in its place: the root signs Site CAs, a Site CA signs
issuing CAs, and an issuing CA signs only certificates that cannot sign anything.

## Finish every ceremony the same way

1. Copy any new key files to **both** key media, and any certificates to the transfer media.
2. Check both key-media copies open: `openssl pkey -in <key> -noout` asks for the passphrase and
   prints nothing on success.
3. Write the date, what was made, and each new certificate's SHA-256 fingerprint in the paper record.
4. Unmount everything and shut the machine down. `/dev/shm/pki` goes with it.
