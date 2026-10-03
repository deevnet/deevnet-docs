---
title: "Preparing"
weight: 1
---

# Preparing

The Root CA, the Site CAs and the issuing CAs are made and signed in **ceremonies**: rare, deliberate
sessions on an **offline machine**, a computer with no network, so a key it touches can only leave on
the media you carry away. Any computer that meets the requirements below will do. This page sets up a
Raspberry Pi 4 with the `pi-pki` image, which is built to meet them, and ends with a Fedora live USB
for working without a Pi.

## What you need

**The offline machine must meet five conditions** (the
[Certificates standard](/docs/standards/certificates/) 5.9):

1. **No network.** No cable connected, Wi-Fi and Bluetooth off, and no network service running.
2. **No remote access and no automation account.** Nothing can reach in, and nothing on it acts for
   a system.
3. **Nothing persists.** It runs from a live or read-only system, works in memory, and forgets
   everything at shutdown. The keys stay on their key media, never on the machine.
4. **A clock you set and confirm.** Every certificate's validity starts from it.
5. **OpenSSL, the signing tool and the profile.** `openssl`, `deevnet-pki-sign`, and
   [`deevnet-pki.cnf`](#signing-profile).

**Three kinds of media keep the keys apart from everything that moves:**

| Media | Holds | Crosses between online and offline? |
|---|---|---|
| **Boot media**: the `pi-pki` microSD, or a live USB | the offline machine's operating system; no key, no certificate | no: written once, then used only on the offline machine |
| **Two key media** (USB drives, the primary and the backup) | the Root CA's and Site CAs' keys | **never**: only ever plugged into the offline machine |
| **Transfer media** (a different USB drive) | signing requests in, certificates out, never a key | yes, and it is the only thing that does; the signing tools fail if they find a key on it |

**You also need a display and keyboard, a paper record, and the passphrase:**

- **a display and a keyboard** for the offline machine, and no network cable;
- **the paper record**, a notebook or sheet, for fingerprints, hashes and dates;
- **the passphrase** for the key files, kept offline, under the holder's own control.

## Raspberry Pi 4

**The `pi-pki` image meets all five conditions by construction, so every session starts from a
known state:**

- `pi-pki` is built by the image factory from Raspberry Pi OS Lite.
- Wi-Fi and Bluetooth are off in firmware, and every network service is masked.
- It has no SSH and no automation account, and one local user.
- Its root is read-only, so nothing done on it survives a reboot.
- It carries `deevnet-pki-sign` and the profile, so the transfer media carries data only, never code
  that runs offline.

A Pi is also small, cheap and easy to keep for nothing but this.

### Flash the image

**Flash it once, and again whenever the image is rebuilt:**

1. Download the image and its hash from the artifact server, and check them. Write the hash in the
   paper record.

   ```bash
   curl -fO http://artifacts.mobile.deevnet.net/pi-images/pki/raspios-bookworm-mobile-pki.img.xz
   curl -fO http://artifacts.mobile.deevnet.net/pi-images/pki/raspios-bookworm-mobile-pki.img.xz.sha256
   sha256sum -c raspios-bookworm-mobile-pki.img.xz.sha256
   ```
2. Flash it to a microSD with Raspberry Pi Imager (choose **no** customization: no Wi-Fi, no SSH, no
   user), or `xzcat raspios-bookworm-mobile-pki.img.xz | sudo dd of=/dev/sdX bs=4M conv=fsync`.

### Start up offline

**Each time, confirm it is offline and set its clock before touching a key:**

1. Put the microSD in the Pi 4, connect the display and keyboard, and power it on. It logs in as
   `pki` on its own and shows the steps.
2. Confirm it has no network:

   ```bash
   ip -brief address           # only lo
   rfkill list                 # no Wi-Fi, no Bluetooth
   ```
3. **Set the clock.** A Pi has no battery clock:

   ```bash
   sudo date -u -s 'YYYY-MM-DD HH:MM'     # now, in UTC
   date -u
   ```
4. Make a working directory in memory, and put the profile in it:

   ```bash
   mkdir -m 0700 /dev/shm/pki && cd /dev/shm/pki
   cp /usr/local/share/deevnet-pki/deevnet-pki.cnf .
   ```
5. Plug in and mount the key media and the transfer media (`lsblk`, then `sudo mount /dev/sdX1
   /mnt/keys` and `sudo mount /dev/sdY1 /mnt/transfer`).

## Signing profile

**One file, `deevnet-pki.cnf`, defines every CA:** the root's name, and the extensions of the root,
the Site CAs and the issuing CAs. The names below the root are given on the command line.

The `pi-pki` image carries it at `/usr/local/share/deevnet-pki/deevnet-pki.cnf`, and a Fedora live
USB gets it on the transfer media. It is printed here so you can check it:

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

**The path lengths keep each layer in its place:** the root signs Site CAs, a Site CA signs
issuing CAs, and an issuing CA signs only certificates that cannot sign anything.

## Finishing up

**Every session ends the same way, with both key copies checked and nothing left behind:**

1. Copy any new key files to **both** key media, and any certificates to the transfer media.
2. Check both key-media copies open: `openssl pkey -in <key> -noout` asks for the passphrase and
   prints nothing on success.
3. Write the date, what was made, and each new certificate's SHA-256 fingerprint in the paper record.
4. Unmount everything and shut the machine down. `/dev/shm/pki` goes with it.

## Fedora live USB

**Without a Pi, a Fedora live USB works on any x86 computer once networking is off.** A current
Fedora Workstation release has `openssl` and keeps nothing after a reboot. It has no signing tools,
so they travel on the transfer media, under its manifest. The [signing profile](#signing-profile)
and [finishing up](#finishing-up) are the same as on the Pi.

### Tools on transfer media

**On the online side, add the tools when preparing the transfer media.** To sign an issuing CA, it is
the [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) step 1 with `--with-tools` added:

```bash
./deevnet-pki-transfer prepare /run/media/$USER/TRANSFER \
  --site mobile --ca substrate --csr /path/to/deevnet-mobile-substrate-ca.csr --with-tools
```

The media then carries `deevnet-pki-sign` and the profile as well as the request, all under its
manifest.

Making the Root CA or a Site CA needs no request. For those, copy `deevnet-pki.cnf` from
`ansible-collection-deevnet.mgmt/scripts/pki/` onto the transfer media, and write its `sha256sum` in
the paper record, to check again on the offline side.

### Start up offline

**Each time, disconnect the network before booting, then confirm it is off and check the clock:**

1. Disconnect the network cable, then boot the computer from the live USB.
2. Turn networking off and confirm it:

   ```bash
   nmcli networking off
   ip -brief address           # only lo
   ```
3. **Check the clock,** and set it if it is wrong:

   ```bash
   date -u
   sudo date -u -s 'YYYY-MM-DD HH:MM'     # only if wrong; now, in UTC
   ```
4. Plug in and mount the key media and the transfer media (`lsblk`, then `sudo mount /dev/sdX1
   /mnt/keys` and `sudo mount /dev/sdY1 /mnt/transfer`).
5. Make a working directory in memory, and copy the profile into it from the transfer media:

   ```bash
   mkdir -m 0700 /dev/shm/pki && cd /dev/shm/pki
   cp /mnt/transfer/deevnet-transfer/to-offline/deevnet-pki.cnf .   # signing an issuing CA
   cp /mnt/transfer/deevnet-pki.cnf .                               # making the Root CA or a Site CA
   sha256sum deevnet-pki.cnf                                        # compare with the paper record
   ```
