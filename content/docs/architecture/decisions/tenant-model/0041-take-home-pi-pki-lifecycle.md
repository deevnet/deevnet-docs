---
title: "ADR-0041: Take-Home Pi PKI Lifecycle"
weight: -41
---

# ADR-0041: A Take-Home Pi Is Managed by the Factory, Independent, or Brings Its Own PKI

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it) and the [decision register](/docs/architecture/reviews/2026-10-tenant-pki/#decision-register) |
| **Date** | 2026-10-21 |
| **Revised** | 2026-10-21, before review: the default is the generic image's, and a card written for a managed tenant sets its mode deliberately; `own` issues device certificates too; the Pi's own services dial canonical names, not `localhost` |
| **Scope** | The certificates on a tenant's take-home Pi and its devices: how each is provisioned, renewed, backed up and recovered under each of three modes, how devices are added away from the factory, and how a tenant moves between modes. Not the tenant CA hierarchy ([ADR-0039](/docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/)), not names ([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/)) |
| **Depends on** | ADR-0039 *(Proposed)* and ADR-0040 *(Proposed)*, for `deevnet` |
| **Related** | [ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/) §4, [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/), the [take-home Pi image](/docs/runbook/tenant/tenant-to-pi-image/), [deevnet-kit](/docs/platforms/deevnet-software/deevnet-kit/), the [Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/) |

---

## Context

**A take-home Pi is a small Deevnet of the tenant's own**: broker, log store and Grafana on one card,
with `deevnet-kit` doing what the API does on a site. Today the kit makes a CA on first boot and
issues the Pi's certificate from it. The certificate names the card's `.local` name, `localhost`,
and every address the Pi has, because a device that cannot resolve a name dials the address.

**Owners want different things.** The owner's own tenants stay under Deevnet's PKI and return to the
factory for maintenance. A meetup attendee may never reconnect. An advanced user may run a CA
already.

## Decision

### 1. Three modes, chosen on the card

| | `deevnet` | `own` | `bring` |
|---|---|---|---|
| For | a Deevnet-managed tenant | a tenant that is, or becomes, independent | a tenant with a PKI of its own |
| Server certificate | a leaf from the tenant's Service CA, for canonical names (and vanity names from the Names CA) | issued by the card's CA | the tenant's |
| Device certificates | from the tenant's Device CA, at the factory | issued by the card's CA, on the Pi | the tenant's |
| Device anchor | the tenant's Service CA | the card's CA | the tenant's |
| Computers trust | the Deevnet Root, already there | the card's CA | the tenant's root |
| Needs the factory | to renew, and to enroll devices by certificate | never | never |
| Deevnet trusts it | yes | no | no |

**The generic image defaults to `own`**, as today: a card with nothing written has no arrangement
with anyone. **A card written for a Deevnet-managed tenant sets `pki=deevnet` deliberately**, as part
of writing that card. It is never left to the default.

### 2. Devices dial an address and verify a name

**A device is given the Pi's address to dial and the broker's canonical name to verify**
(`mqtt.<tenant>.t.deevnet.net`). mbedTLS sets the expected name apart from the address. ESP-MQTT and
MicroPython expose it, and it also becomes the SNI. So no certificate needs an address in it, and
the home network needs no DNS for the tenant's names.

**The Pi's own services dial canonical names too**, mapped to the loopback address on the Pi. So no
certificate needs `localhost`, which the tenant subtree does not permit.

**Under `own`, the card's certificate may keep addresses**, for devices that cannot set a name apart.

### 3. `deevnet`: the Pi holds leaves and renews at maintenance

**At provisioning**, on the factory's network or with the API reachable:
1. the kit makes the server key and a request for the tenant's canonical names (and any vanity
   names);
2. the owner sends the request with the tenant's token;
3. the kit installs each leaf with its chain.

**No CA key is on the card.**

**Renewal is the same three steps, each year, inside the window.** `deevnet-kit status` warns from
60 days. A request and a certificate are public and may travel on a USB stick. The token, which is
what authorizes, stays with the owner.

**A device added away from the factory gets a password account** (`deevnet-kit account add`), as
today. It gets a certificate from its Device CA at the next maintenance.

**A failed card**: a new card, a new key, a leaf at the next maintenance. Until then the service is
down. Options, the owner's:
- back up the leaf's key and certificate when issued;
- a longer leaf for take-home, up to what clients accept (825 days on Apple platforms, to confirm).

### 4. `own`: the tenant's authority, and where its key lives

**The card's CA issues and renews both server and device certificates, with no contact with
Deevnet.** A device enrolls on the Pi (`deevnet-kit device enroll`). Renewal is local and automatic,
because the authority is local.

**Its CA is constrained to the tenant's canonical subtree and private addresses**, which costs
nothing and binds every client that enforces it.

**Where the CA key lives:**

| Option | |
|---|---|
| **A CA on the card, with an encrypted backup taken at first boot** *(leaning)* | `deevnet-kit ca backup` writes the CA key, passphrase-encrypted, to the owner's USB stick. The kit does not finish first boot until a backup exists, and the owner is told to keep it off the Pi. A failed card is restored from it, and no device changes anchor |
| A root the owner keeps off the Pi, and an issuing CA on the card | A lost or stolen card costs an issuing CA, not the anchor: devices that trust the owner's root accept the replacement. More to understand and to keep; worth it for a tenant with many devices |
| A CA on the card, no backup (today) | A failed card means every device takes a new anchor |

**A backup counts only once a restore from it has worked.** The kit can check a backup by loading it
on the same card.

### 5. `bring`: the tenant's PKI, the kit's mechanics

**The kit takes a leaf and chain, or an issuing CA, and an anchor for devices.** It renews nothing it
did not issue. Deevnet holds nothing of it and trusts none of it.

### 6. Changing mode is a trust transition, in order

**From `deevnet` to `own` or `bring` (graduation), or back:**
1. The new anchor reaches every device and computer **beside** the old one.
2. The Pi's certificates are reissued by the new authority.
3. Once every device is known to hold the new anchor, the old one is removed.

**The service stays up throughout**, because each device trusts both while it matters. **Deevnet's
keys are never handed over**: independence is a new authority. A device that can take an anchor only
by cable is provisioned again at step 1. How a device takes an anchor is its application's
(ADR-0011).

---

## Consequences

**Every take-home Pi chooses its relationship with Deevnet**, deliberately when managed, and can
change it.

**Under `deevnet`, uptime depends on a visit a year**, or less often with a longer leaf.

**Under `own`, the backup is what stands between a failed card and re-anchoring every device.**

**The kit grows**: `pki=`; a request and install path; a CA backup and its check; device enrollment;
a constraint on its own CA; canonical names in place of `localhost` and addresses.

---

## Alternatives considered

- **Rejected: every take-home Pi is managed by Deevnet.** Some owners never come back.
- **Rejected: every take-home Pi is independent.** The owner's own tenants would each carry a root.
- **Rejected: under `deevnet`, the Pi holds the tenant's Service CA** (ADR-0039).

---

## Open questions

1. **`own`: a CA on the card with a backup, or an owner-held root** (§4)?
2. **`deevnet`: a longer leaf, or a key backup** (§3)?
3. **`bring`: an issuing CA, or leaves only?**

---

## What would settle it

V1, V7, V8 and V11 of the
[validation plan](/docs/architecture/reviews/2026-10-tenant-pki/#validation-plan).
