---
title: "Custody"
weight: 5
---

# Custody

The Root CA's and every Site CA's keys exist only as passphrase-encrypted files on two key media,
kept apart. The passphrase is kept offline, under the holder's own control, and never with the key
media.

## Storage

- **Primary key media:** in the holder's secure storage.
- **Backup key media:** somewhere else, so one loss (fire, theft, a bag left behind) cannot take both.
- **The paper record:** fingerprints and dates of every certificate the ceremonies made. It is how
  you recognize the right file, and how anyone checks a certificate they were handed.

Neither key media is ever plugged into a networked machine.

## Every year

On the offline machine ([Preparing](/docs/runbook/root-of-trust/preparing/)):

```bash
openssl pkey -in /path/to/primary/deevnet-root-ca.key -noout
openssl pkey -in /path/to/backup/deevnet-root-ca.key -noout
# and each deevnet-<site>-site-ca.key, on both
```

Each asks for the passphrase and prints nothing. Note the date in the paper record. A copy that does
not open is replaced from the other at once, by copying the file, never by generating a new key.

Check the calendar too: an issuing CA lasts five years, a Site CA ten, the root twenty. Rotate each a
year before it expires.

## If a key media is lost

The keys on it are encrypted, so a lost drive alone exposes nothing while the passphrase is safe.
Copy the surviving media onto a new drive, and note it in the paper record.

## If a key may be exposed

That is, the file *and* the passphrase may both have been seen.

- **A Site CA's key:** make a new Site CA ([Site CA](/docs/runbook/root-of-trust/site-ca/)), sign new
  issuing CAs under it, and reissue the site's certificates. Clients keep trusting the root, so
  nothing is handed out.
- **The root's key:** everything is re-rooted: a new root, new Site CAs, new issuing CAs, and the new
  root handed to every machine, tenant and computer that trusts the old one. Record it as an incident.

## If both copies are lost

Certificates already issued keep working until they expire, but nothing new can be signed above the
issuing CAs. For a Site CA, make a new one. For the root, it is the re-root above.
