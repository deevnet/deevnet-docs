---
title: "Root and Site CA Ceremony"
weight: 1
aliases:
  - /docs/runbook/root-of-trust/preparing/
  - /docs/runbook/root-of-trust/root-ca/
  - /docs/runbook/root-of-trust/site-ca/
---

# Root and Site CA Ceremony

The Deevnet Root CA and each site's Site CA are made in a **ceremony**: a rare, deliberate session
on an **offline machine**, a computer with no network, so a key it touches can only leave on the
drives you carry away. On the `pi-pki` image a script, `./deevnet-pki-ceremony.sh`, walks the whole
session step by step and asks before each step. This page is what you need, how to start, what the
script does, and the commands it runs.

## What you need

**Gather everything before you start; the Pi never touches a network:**

| Item | Notes |
|---|---|
| **Raspberry Pi 4 Model B** | any memory size |
| **Its USB-C power supply** | the official 5.1 V / 3 A supply, or one as good |
| **microSD card**, 8 GB or larger | flashed with the `pi-pki` image ([below](#flash-the-ceremony-image)); holds the system, never a key |
| **HDMI display and a micro-HDMI to HDMI cable** | the Pi 4's display ports are micro-HDMI; use the one nearest the power port |
| **Wired USB keyboard** | wired: a wireless keyboard is a radio link |
| **Two USB drives, plus one more for a backup** | the **key drive** (encrypted, holds the CA keys), the **transfer drive** (plain, carries certificates to the Builder), and optionally a **backup key drive**. Any size; label them with a marker so you can tell them apart |
| **No network cable** | nothing is ever plugged into the Pi's network port |
| **The paper record and a pen** | a notebook or sheet, for fingerprints, hashes and dates |
| **Two passphrases, chosen beforehand** | one for the key drive, one for the key files inside it; both kept offline, under the holder's own control |

**Opening a key drive later needs only the drive and both passphrases, on any Linux machine with
`cryptsetup`.** That is the `pi-pki` image on any Pi, or a Fedora live USB on any computer. Nothing
ties a key drive to the Pi or the microSD that made it: there is no TPM and no key file kept
anywhere else. Lose the drive's passphrase, though, and that drive is unreadable; the backup key
drive is the only way back.

**Each drive has one job:**

| Drive | Holds | Crosses between online and offline? |
|---|---|---|
| **microSD** (boot) | the `pi-pki` system | no: written once, then used only in the Pi |
| **Key drive**, and the **backup key drive** (LUKS2-encrypted) | the Root CA's and Site CAs' passphrase-encrypted keys, and their certificates | **never**: only ever plugged into the Pi |
| **Transfer drive** (plain FAT32, labeled `TRANSFER`) | certificates out, signing requests in, never a key | yes, and it is the only thing that does |

## The ceremony machine

**The offline machine must meet five conditions** (the
[Certificates standard](/docs/standards/certificates/) 5.9):

1. **No network.** No cable connected, Wi-Fi and Bluetooth off, and no network service running.
2. **No remote access and no automation account.** Nothing can reach in, and nothing on it acts for
   a system.
3. **Nothing persists.** It runs from a live or read-only system, works in memory, and forgets
   everything at shutdown. The keys stay on their key drives, never on the machine.
4. **A clock you set and confirm.** Every certificate's validity starts from it.
5. **OpenSSL, the tools and the profile.** `openssl` and the [signing profile](#signing-profile).

**The `pi-pki` image meets all five by construction:**

- It is built by the image factory from Raspberry Pi OS Lite.
- Wi-Fi and Bluetooth are off in firmware, and every network service is masked.
- It has no SSH and no automation account, only the `pki` user, logged in on the screen.
- Its root is read-only under a RAM overlay, so nothing done on it survives a reboot.
- It carries the tools, so the transfer drive carries data only:
  - `/home/pki/deevnet-pki-ceremony.sh`, the ceremony;
  - `/usr/local/bin/deevnet-pki-media.sh`, which prepares and opens the drives;
  - `/usr/local/bin/deevnet-pki-sign.sh`, for the [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/);
  - `/usr/local/share/deevnet-pki/deevnet-pki.cnf`, the profile.

### Flash the ceremony image

**Flash it once, and again whenever the image is rebuilt:**

1. Download the image and its hash from the artifact server, and check them. Write the hash in the
   paper record.

   ```bash
   curl -fO http://artifacts.mobile.deevnet.net/pi-images/pki/raspios-bookworm-mobile-pki.img.xz
   curl -fO http://artifacts.mobile.deevnet.net/pi-images/pki/raspios-bookworm-mobile-pki.img.xz.sha256
   sha256sum -c raspios-bookworm-mobile-pki.img.xz.sha256
   ```
2. Flash it to the microSD with Raspberry Pi Imager (choose **no** customization: no Wi-Fi, no SSH,
   no user), or `xzcat raspios-bookworm-mobile-pki.img.xz | sudo dd of=/dev/sdX bs=4M conv=fsync`.

## Run the ceremony

**Start with no USB drive plugged in; the script asks for each one when it needs it:**

1. Put the microSD in the Pi and connect the display, keyboard and power, with no network cable
   and no USB drive. It boots to the `pki` login on its own and shows a banner.
2. Set the clock. A Pi has no battery clock, and every certificate's validity starts from it:

   ```bash
   sudo date -u -s 'YYYY-MM-DD HH:MM'     # now, in UTC
   ```
3. Run the ceremony:

   ```bash
   ./deevnet-pki-ceremony.sh
   ```

**The script explains each step and asks Proceed? [Y/n] before it runs it.** Answering `n` stops
it cleanly. In order, it:

1. **asks which path:**
   - **1:** a new Deevnet Root CA, then a Site CA (the first ceremony, or a re-root);
   - **2:** a Site CA only, signed by the root already on the key drive (a new site, or a Site CA
     rotation);
   - **3:** sign an issuing CA from a request the Builder put on the transfer drive
     ([Issuing CA](/docs/runbook/root-of-trust/issuing-ca/)); the rest of this list is paths 1
     and 2;
2. **checks the Pi is offline**, shows the clock, and asks you to confirm it;
3. **makes the working directory** in RAM, `/dev/shm/pki`, gone at power-off;
4. **asks for the key drive, then the transfer drive.** For each, insert it when asked. One already
   made is recognized and opened; any other drive is formatted, only after you agree (that erases
   it). The key drive asks for its passphrase, twice when it is new;
5. **makes the Root CA** (path 1), in four steps:
   - generates the key (asks for the key passphrase twice);
   - self-signs it;
   - shows the certificate and its fingerprint, and **waits until you have written it in the paper
     record**;
   - stores the key and certificate on the key drive, checks the key opens, and puts the
     certificate alone on the transfer drive;
6. **makes the Site CA** the same way, after asking the site's name (`mobile`, `home`, …), signed
   by the root's key (it asks for the root key's passphrase), and checks it chains to the root;
7. **offers the backup key drive.** It is optional. If you have it, take out the primary when asked
   and insert the backup; everything on the primary is copied onto it. If not, make it
   [later](#a-backup-key-drive-later);
8. **finishes:** lists what is on the transfer drive and everything for the paper record, closes
   both drives, and offers to power off.

It never overwrites a key: a key drive that already holds the CA it would make stops it.

## After the ceremony

**Only the certificates go to automation, never a key:**

1. Plug the transfer drive into the Builder, and mount it:

   ```bash
   sudo mkdir -p /mnt/transfer && sudo mount LABEL=TRANSFER /mnt/transfer
   ```
2. The certificates go into the inventory, through a pull request like any other inventory change:
   - `deevnet-root-ca.pem` at `pki/deevnet-root-ca.pem`;
   - `deevnet-<site>-site-ca.pem` at `pki/<site>/deevnet-<site>-site-ca.pem`.

   Check each one's fingerprint against the paper record first.
3. Keep the key drives apart, as [Custody](/docs/runbook/root-of-trust/custody/) says.

Next: the site's [issuing CAs](/docs/runbook/root-of-trust/issuing-ca/).

### A backup key drive later

**A backup key drive can be made after the ceremony.** Until it exists, each key exists only once,
and losing that drive means making the CAs again. The script offers the backup at the end of every
session. On its own, on the Pi:

```bash
mkdir -m 0700 /dev/shm/pki && cd /dev/shm/pki
sudo deevnet-pki-media.sh keys open primary && cp /mnt/keys/deevnet-* . && sudo deevnet-pki-media.sh keys close
# take out the primary, insert the new drive; deevnet-pki-media.sh list shows its name
sudo deevnet-pki-media.sh keys init /dev/sdX backup      # opens it at /mnt/keys
cp deevnet-* /mnt/keys/ && sudo deevnet-pki-media.sh keys close
```

## What the script runs

**These are the script's commands, for reading, checking, or running by hand.** They run in
`/dev/shm/pki` with the key drive open at `/mnt/keys` and the transfer drive at `/mnt/transfer`.

### The drives

```bash
sudo deevnet-pki-media.sh list                          # USB drives, and what each holds
sudo deevnet-pki-media.sh keys init /dev/sdX primary    # ERASES: LUKS2 + ext4, label deevnet-keys-primary
sudo deevnet-pki-media.sh keys open                     # unlock, mount at /mnt/keys
sudo deevnet-pki-media.sh transfer init /dev/sdY        # ERASES: FAT32, label TRANSFER
sudo deevnet-pki-media.sh transfer mount                # /mnt/transfer
sudo deevnet-pki-media.sh keys close; sudo deevnet-pki-media.sh transfer umount
```

`init` refuses anything but a whole USB drive, anything mounted and the boot card, and erases only
after you type the device's name. A key drive's key-derivation cost is fixed and modest, so any
machine can unlock it.

### The Root CA

**RSA 4096, twenty years, `O=Deevnet, OU=Deevnet PKI, CN=Deevnet Root CA`:**

```bash
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:4096 -aes-256-cbc -out deevnet-root-ca.key
openssl req -x509 -new -config deevnet-pki.cnf -key deevnet-root-ca.key \
  -extensions v3_root -days 7305 -sha256 \
  -set_serial 0x$(openssl rand -hex 16) \
  -out deevnet-root-ca.pem
openssl x509 -in deevnet-root-ca.pem -noout -subject -issuer -enddate -ext basicConstraints,keyUsage
openssl x509 -in deevnet-root-ca.pem -noout -fingerprint -sha256
cp deevnet-root-ca.key deevnet-root-ca.pem /mnt/keys/
openssl pkey -in /mnt/keys/deevnet-root-ca.key -noout    # the key opens; prints nothing
cp deevnet-root-ca.pem /mnt/transfer/
```

Check:
- subject and issuer both read `O = Deevnet, OU = Deevnet PKI, CN = Deevnet Root CA`;
- it ends twenty years from today;
- `CA:TRUE, pathlen:2`, and `Certificate Sign, CRL Sign`.

### A Site CA

**RSA 3072, ten years, `O=Deevnet, OU=<Site> Site, CN=Deevnet <Site> Site CA`, signed by the root.**
The site's name is its title in the [naming standard](/docs/standards/naming/):

```bash
SITE=Mobile; site=mobile
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -aes-256-cbc \
  -out deevnet-$site-site-ca.key
openssl req -new -key deevnet-$site-site-ca.key \
  -subj "/O=Deevnet/OU=$SITE Site/CN=Deevnet $SITE Site CA" \
  -out deevnet-$site-site-ca.csr
openssl x509 -req -in deevnet-$site-site-ca.csr \
  -CA /mnt/keys/deevnet-root-ca.pem -CAkey /mnt/keys/deevnet-root-ca.key \
  -extfile deevnet-pki.cnf -extensions v3_site -days 3653 -sha256 \
  -set_serial 0x$(openssl rand -hex 16) \
  -out deevnet-$site-site-ca.pem
openssl verify -CAfile /mnt/keys/deevnet-root-ca.pem deevnet-$site-site-ca.pem
openssl x509 -in deevnet-$site-site-ca.pem -noout -fingerprint -sha256
cp deevnet-$site-site-ca.key deevnet-$site-site-ca.pem /mnt/keys/
openssl pkey -in /mnt/keys/deevnet-$site-site-ca.key -noout
cp deevnet-$site-site-ca.pem /mnt/transfer/
```

The extensions come only from the profile, never from the request. Check:
- subject `O = Deevnet, OU = Mobile Site, CN = Deevnet Mobile Site CA`, issuer the root;
- `CA:TRUE, pathlen:1`, ten years;
- Name Constraints permit only `deevnet.net`, `localhost`, and the private and loopback ranges;
- `verify` answers `OK`.

### Signing profile

**One file, `deevnet-pki.cnf`, defines every CA:** the root's name, and the extensions of the root,
the Site CAs and the issuing CAs. The names below the root are given on the command line. The
`pi-pki` image carries it at `/usr/local/share/deevnet-pki/deevnet-pki.cnf`; it is printed here so
you can check it:

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
nameConstraints        = @site_names

# Everything under a Site CA may name only Deevnet's own names and private
# addresses: a leaked key below it cannot vouch for a public site. Not marked
# critical: mbedTLS (ESP-IDF, MicroPython) does not implement name constraints
# and refuses to parse a certificate with a critical extension it does not
# know, so a critical one would cut off every such device. OpenSSL, Go, Java,
# Rust, Erlang, browsers and Windows enforce it either way.
[ site_names ]
permitted;DNS.1 = deevnet.net
permitted;DNS.2 = localhost
permitted;IP.1  = 10.0.0.0/255.0.0.0
permitted;IP.2  = 172.16.0.0/255.240.0.0
permitted;IP.3  = 192.168.0.0/255.255.0.0
permitted;IP.4  = 127.0.0.0/255.0.0.0
permitted;IP.5  = fc00::/fe00::
permitted;IP.6  = ::1/ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff

[ v3_issuing ]
basicConstraints       = critical, CA:TRUE, pathlen:0
keyUsage               = critical, keyCertSign, cRLSign
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always
```

**The Site CA's name constraints keep everything under it to Deevnet's own names and private
addresses**, so no key below it can vouch for a public site. They are not marked critical, so devices
whose TLS library does not implement them (mbedTLS) can still parse the chain.

**The path lengths keep each layer in its place:** the root signs Site CAs, a Site CA signs
issuing CAs, and an issuing CA signs only certificates that cannot sign anything.

## What this protects, and what it does not

**The ceremony keeps the Root CA's and Site CAs' keys off every networked machine.** They are made on
a machine with no network, kept encrypted on drives that only ever go into that machine, and never
cross to the online side. A compromise of any site system, automation included, cannot make a new
CA.

**It does not protect against a compromised Builder.** The ceremony image is built on the Builder,
from packages fetched at build time and the scripts in git, and its hash is published by the same
Builder: the hash proves the card is what the Builder made, not that what it made is honest. Code
planted there would run on the offline machine and could weaken the root it makes. What Deevnet does
about it:

- **The tools are short, readable shell.** Read `deevnet-pki-ceremony.sh`, `deevnet-pki-media.sh`
  and the profile before a ceremony; the commands it runs are on this page.
- **The image records what it carries:** `/etc/deevnet-pki-release` names its build date and the
  tools' git commit. Write both, and the image's hash, in the paper record.
- **Keep the microSD that made the root.** It is evidence of what ran.

What it does not do: build the image on a second, independent machine and compare, or sign it with
a key held off the Builder. A site that needs that assurance should add it.

**It cuts some corners, knowingly.** This is a lab, not a vault:
- one person holds both offline keys, both passphrases and the vault password;
- the root and Site CA keys share one key drive and one passphrase;
- the ceremony machine was built and flashed from the Builder, and during setup a key drive went
  into the Builder for testing. Once a real root exists, its key drives never touch a networked
  machine.

**There is no revocation.** A CA certificate stays valid until it expires; see
[Custody](/docs/runbook/root-of-trust/custody/#exposed-key) for what an exposed key means, and when to
re-root.

## Without a Pi: a Fedora live USB

**A Fedora live USB on any x86 computer works too, by hand.** A current Fedora Workstation release
has `openssl` and `cryptsetup` and keeps nothing after a reboot, but not the Deevnet tools: run
[the commands above](#what-the-script-runs) yourself, with the drives opened by hand.

1. Disconnect the network cable, boot the computer from the live USB, and turn networking off:

   ```bash
   nmcli networking off
   ip -brief address           # only lo
   ```
2. Check the clock with `date -u`, and set it if it is wrong (`sudo date -u -s 'YYYY-MM-DD HH:MM'`).
3. Bring the profile on the transfer drive: on the Builder, copy `deevnet-pki.cnf` from
   `ansible-collection-deevnet.mgmt/scripts/pki/` onto it, and write its `sha256sum` in the paper
   record.
4. Open the drives (`lsblk` finds each):

   ```bash
   sudo cryptsetup open /dev/sdX deevnet-keys && sudo mkdir -p /mnt/keys \
     && sudo mount /dev/mapper/deevnet-keys /mnt/keys      # the key drive's passphrase
   sudo mkdir -p /mnt/transfer && sudo mount /dev/sdY1 /mnt/transfer
   mkdir -m 0700 /dev/shm/pki && cd /dev/shm/pki
   cp /mnt/transfer/deevnet-pki.cnf . && sha256sum deevnet-pki.cnf   # compare with the paper record
   ```

   A new key drive is made with `sudo cryptsetup luksFormat --type luks2 --label deevnet-keys-primary
   /dev/sdX`, then `mkfs.ext4` on the opened device.
5. At the end: `sudo umount /mnt/keys && sudo cryptsetup close deevnet-keys`, unmount the transfer
   drive, and power off.

For an [issuing CA](/docs/runbook/root-of-trust/issuing-ca/) on Fedora, the transfer drive also
brings `deevnet-pki-sign.sh` (`deevnet-pki-transfer.sh prepare … --with-tools`).
