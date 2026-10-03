---
title: "Preparing"
weight: 1
---

# Preparing

Every ceremony runs on a machine with no network, so a key it touches can only leave on the media
you carry away.

## What you need

| Media | Holds | Crosses between online and offline? |
|---|---|---|
| **microSD** with the ceremony image | the offline machine's operating system and the ceremony's tools; no key, no certificate | no: written once when flashed, then only in the Pi |
| **Two key media** (USB drives, the primary and the backup) | the Root CA's and Site CAs' keys | **never**: only ever plugged into the offline machine |
| **Transfer media** (a different USB drive) | signing requests in, certificates out, never a key | yes, and it is the only thing that does; the ceremony's tools fail if they find a key on it |

And:

- **A Raspberry Pi 4**, an HDMI display, a USB keyboard and its power supply. No network cable.
- **The paper record**, a notebook or sheet, for fingerprints, hashes and dates.
- **The passphrase** for the key files, kept offline, under the holder's own control.

## The ceremony image

The offline machine's operating system is `pi-pki`, built by the image factory: Raspberry Pi OS Lite
with Wi-Fi and Bluetooth off in firmware, every network service masked, no SSH, no automation
account, one local user, and a read-only root, so nothing a ceremony does survives a reboot. It
carries the signing tool, `deevnet-pki-sign`, and this page's profile.

Flash it once, and again whenever it is rebuilt:

1. Download `pi-images/pki/raspios-bookworm-mobile-pki.img.xz` and its `.sha256` from the artifact
   server, and check them: `sha256sum -c raspios-bookworm-mobile-pki.img.xz.sha256`. Write the hash
   in the paper record.
2. Flash it to a microSD with Raspberry Pi Imager (choose **no** customization: no Wi-Fi, no SSH, no
   user), or `xzcat raspios-bookworm-mobile-pki.img.xz | sudo dd of=/dev/sdX bs=4M conv=fsync`.

## Bring up the offline machine

1. Put the microSD in the Pi 4, connect the display and keyboard, and power it on. It logs in as
   `pki` on its own and shows the steps.
2. Confirm it has no network:

   ```bash
   ip -brief address           # only lo
   rfkill list                 # no Wi-Fi, no Bluetooth
   ```
3. **Set the clock.** A Pi has no battery clock, and every certificate's validity starts from it:

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

### Without a Pi: a Fedora live USB

Any x86 machine works the same way, booted from a live USB of a current Fedora Workstation release
(it has `openssl`, and nothing it does survives a reboot):

- turn networking off and confirm it (`nmcli networking off`, `ip -brief address` shows only `lo`),
  check `date -u`, and make `/dev/shm/pki` as above;
- the live USB has no ceremony tools, so prepare the transfer media with
  `deevnet-pki-transfer prepare … --with-tools`. It then carries `deevnet-pki-sign` and the profile,
  under its manifest, and you copy the profile into `/dev/shm/pki` from there.

## The profile file

Every ceremony uses this file, `deevnet-pki.cnf`. The ceremony image carries it at
`/usr/local/share/deevnet-pki/deevnet-pki.cnf`, and it is here so you can check it. It holds the
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
