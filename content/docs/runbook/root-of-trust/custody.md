---
title: "Custody"
weight: 5
---

# Custody

The Root CA's and every Site CA's keys exist only as passphrase-encrypted files on two encrypted key
drives, kept apart. Both passphrases, the drives' and the key files', are kept offline, under the
holder's own control, and never with the key media.

## Two key media

**The keys live on two key media, kept apart:**

- **Primary key media:** in the holder's secure storage.
- **Backup key media:** somewhere else, so one loss (fire, theft, a bag left behind) cannot take both.
- **The paper record:** fingerprints and dates of every certificate the ceremonies made. It is how
  you recognize the right file, and how anyone checks a certificate they were handed.

Neither key media is ever plugged into a networked machine.

**Opening a key drive needs only the drive and both passphrases, on any Linux machine with
`cryptsetup`:** the `pi-pki` image on any Pi, or a Fedora live USB. Nothing ties a drive to the Pi
or microSD that made it ([Preparing](/docs/runbook/root-of-trust/preparing/#prepare-new-media)).

## Yearly check

**Every year, check that both copies still open.** On the offline machine ([Preparing](/docs/runbook/root-of-trust/preparing/)):

```bash
sudo deevnet-pki-media keys open primary          # the drive's passphrase
openssl pkey -in /mnt/keys/deevnet-root-ca.key -noout
openssl pkey -in /mnt/keys/deevnet-mobile-site-ca.key -noout   # and each other site's
sudo deevnet-pki-media keys close
# then the same with: keys open backup
```

Each `openssl pkey` asks for the key's passphrase and prints nothing. Note the date in the paper record. A copy that does
not open is replaced from the other at once, by copying the file, never by generating a new key.

## Rotation calendar

**Each CA is rotated a year before it expires.** At the yearly check, also check the calendar:

| CA | Its key is held by | Signs | Valid for | Rotate it |
|---|---|---|---|---|
| Deevnet Root CA | the operator, offline | Site CAs | twenty years | 19 years after it was made |
| Site CA | the operator, offline | its site's issuing CAs | ten years | 9 years after it was made |
| Substrate CA | site automation | every substrate server certificate | five years | 4 years after it was made |
| Tenant Device CA | the site's secret store | tenant devices' client certificates | five years | 4 years after it was made |

Rotating a CA means making a new one with the same ceremony:
- [Site CA](/docs/runbook/root-of-trust/site-ca/) for a Site CA;
- [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) for an issuing CA.

## What a rotation reaches

**A rotation reaches everything below the CA rotated, and nothing above it.** A certificate works
only while every CA above it is still valid. When a CA expires, everything it
signed stops working with it, however long those certificates had left. A rotation therefore has to
move everything below the rotated CA onto the new one before the old one expires. The year's head
start is for that.

| Rotating | Made again | Reissued | Handed out | Who notices |
|---|---|---|---|---|
| **Deevnet Root CA** | the root, every site's Site CA, and every site's issuing CAs | every certificate at every site | the new root, to every trust store that holds the old one: substrate hosts, operator computers, tenants' computers and Pis, device firmware | everyone: each trust store must take the new root before the old one expires |
| **Site CA** | that site's Site CA and both its issuing CAs | every certificate at that site | nothing: the root is unchanged | only that site's services, as automation reinstalls their chains |
| **Substrate CA** | that site's Substrate CA | that site's substrate server certificates | nothing | no one: the certificates roll over at their yearly renewal |
| **Tenant Device CA** | that site's Tenant Device CA | that site's tenant device certificates | nothing | no one: devices pick up new certificates at their yearly renewal |

**A Deevnet Root CA rotation runs the old and new roots side by side.**
1. Make the new root.
2. Make the Site CAs and issuing CAs under it, site by site.
3. Install the new root beside the old one in every trust store.
4. Reissue every certificate under the new chain.
5. Remove the old root only once nothing uses it.

Treat it as a planned change of its own.

**A Site CA rotation reaches only its own site.**
1. Make the new Site CA.
2. Sign new Substrate and Tenant Device CAs under it.
3. Reissue every certificate at the site before the old Site CA expires.

Clients trust the root, not the Site CA, so nothing is handed out. Other sites are untouched.

**An issuing CA rotation is absorbed by ordinary renewal.** Certificates last a year and are
reissued once fewer than 60 days remain
([Certificates standard](/docs/standards/certificates/) 4.7). Once automation issues from the new
CA, every certificate moves to it within the year, before the old CA expires. The old and new CAs
both chain to the same Site CA and root, so clients trust both while they overlap.

These are planned rotations, with the old key still safe. A key that may have been exposed is
[replaced at once](#exposed-key), without waiting for the calendar.

## Lost key media

**A lost key media exposes nothing while the passphrases are safe,** because the drive is encrypted
and so is each key file on it.
Copy the surviving media onto a new drive, and note it in the paper record.

## Exposed key

**An exposed key is replaced, never reused.** A key is exposed when the file *and* the passphrase
may both have been seen.

- **A Site CA's key:** make a new Site CA ([Site CA](/docs/runbook/root-of-trust/site-ca/)), sign new
  issuing CAs under it, and reissue the site's certificates. Clients keep trusting the root, so
  nothing is handed out.
- **The root's key:** everything is re-rooted: a new root, new Site CAs, new issuing CAs, and the new
  root handed to every machine, tenant and computer that trusts the old one. Record it as an incident.

## Both copies lost

**Losing both copies of a key stops new signing at that level.** Certificates already issued keep working until they expire, but nothing new can be signed above the
issuing CAs. For a Site CA, make a new one. For the root, it is the re-root above.
