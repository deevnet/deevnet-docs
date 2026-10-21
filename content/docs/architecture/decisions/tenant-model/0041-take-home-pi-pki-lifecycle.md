---
title: "ADR-0041: Take-Home Pi PKI Lifecycle"
weight: -41
---

# ADR-0041: A Take-Home Pi Is Managed by the Factory, Independent, or Brings Its Own PKI

|  |  |
|--|--|
| **Status** | Proposed. Nothing is built; see [What would settle it](#what-would-settle-it) |
| **Date** | 2026-10-21 |
| **Scope** | The certificates on a tenant's take-home Pi and its devices: how each is provisioned, renewed and recovered under each of three choices, how devices are added away from the factory, and how a tenant moves from one choice to another. Not the tenant CA hierarchy ([ADR-0039](/docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/)) and not names ([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/)) |
| **Depends on** | [ADR-0039](/docs/architecture/decisions/substrate/0039-tenants-beside-sites-in-the-pki/) *(Proposed)* for the `deevnet` choice |
| **Related** | [ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/) §4 (applications read the CA from a variable), [ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) (devices are their application's), the [take-home Pi image](/docs/runbook/tenant/tenant-to-pi-image/), [deevnet-kit](/docs/platforms/deevnet-software/deevnet-kit/), the [Tenant PKI review](/docs/architecture/reviews/2026-10-tenant-pki/) |

---

## Context

**A take-home Pi is a small Deevnet of the tenant's own**: broker, log store and Grafana on one card,
with `deevnet-kit` doing what the API does on a site. On first boot the kit makes a CA for the card
and issues the Pi's server certificate from it. That certificate names the card's `.local` name,
`localhost`, and every address the Pi has, because a device that cannot resolve a name dials the
address and verifies it.

**Not every tenant that takes a Pi home wants the same thing.** The owner's own tenants stay under
Deevnet's PKI and come back to the factory for maintenance. A meetup attendee may never reconnect. An
advanced user may already run a CA. Today the kit offers only the second.

## Decision

### 1. The card chooses, with `pki=`

| | `deevnet` | `own` | `bring` |
|---|---|---|---|
| For | a Deevnet-managed tenant | a tenant that is, or will be, independent | a tenant with a CA of its own |
| Server certificate | a leaf from the tenant's Service CA (ADR-0039), asked for through the API | issued by the card's own CA, as today | the tenant's leaf and chain, or issued by the tenant's CA |
| Device anchor | the tenant's Service CA | the card's CA | the tenant's |
| Computers trust | the Deevnet Root, already there | the card's CA | the tenant's root |
| Needs the factory | to renew, and for device certificates | never | never |

**`own` is the default**, because a card with no choice written is one whose owner made no
arrangement with anyone. A tenant may change its choice later (§6).

### 2. Devices dial an address and verify a name

**A device is given the Pi's address to dial and the broker's name to verify.** mbedTLS takes the
expected name apart from the address it connects to (and ESP-MQTT and MicroPython expose it). So no
certificate needs an address in it, the home network needs no DNS for the tenant's names, and a
certificate from the tenant's Service CA, which names only the tenant's zone, serves a Pi on any
network.

**Under `own` the card's certificate keeps its addresses** for devices that cannot do this.

### 3. `deevnet`: the Pi holds a leaf, and renews at maintenance

**At provisioning**, while the Pi is on the factory's network or the owner's computer can reach
the API:
1. the kit makes the server key and a request for the tenant's broker, log and Grafana names;
2. the owner sends the request with the tenant's token;
3. the kit installs the leaf and its chain.

**The key never leaves the card.**

**Renewal is the same three steps, each year**, inside the window. `deevnet-kit status` warns from 60
days. The request and the certificate are public, so they may travel on a USB stick. The token,
which authorizes, stays with the owner.

**A device added away from the factory gets a password account** (`deevnet-kit account add`), as
today, and a certificate from its tenant's Device CA at the next maintenance. The broker accepts
both until the tenant chooses otherwise.

**A card that fails** is replaced by a new card: a new key, and a leaf at the next maintenance.
Until then the service is down. Options, not decided:
- the owner backs up the leaf's key and certificate when it is issued (one more copy of a key);
- a longer leaf for take-home, so maintenance is rarer, up to what clients accept (825 days on
  Apple platforms, to confirm).

### 4. `own`: the tenant's authority, and where its key lives

**Whether the Pi should hold a CA key at all** is this record's main open choice:

| Option | |
|---|---|
| **A CA on the card, with an encrypted backup taken at first boot** *(leaning, for meetup attendees)* | As today, plus `deevnet-kit ca backup` to the owner's USB stick, passphrase-protected. A failed card is restored from it, and no device changes anchor |
| A root the owner keeps off the Pi, and an issuing CA on the card | A lost card costs an issuing CA, not the anchor. More to understand and to keep |
| A CA on the card, no backup (today) | A failed card means every device gets a new anchor |

**Its CA is constrained to the tenant's names and private addresses**, which costs nothing and
binds every client that enforces it.

**It issues device certificates too**, from the same card, when the kit grows device certificates.
Until then, devices use passwords as they do today.

### 5. `bring`: the tenant's PKI, the kit's mechanics

**The kit takes a leaf and its chain, or an issuing CA**, and an anchor for its devices. It
renews nothing it did not issue; the tenant does. Deevnet holds nothing of it.

### 6. Changing choice is a trust transition, done in order

**From `deevnet` to `own` or `bring`, and back:**
1. The new anchor is given to every device and computer, **beside** the old one.
2. The Pi's certificate is reissued from the new authority.
3. Once every device is known to hold the new anchor, the old one is removed.

The service is up throughout, because each device trusts both while it matters. **Deevnet's keys
are never handed over**: independence is a new authority, not a copy of the old.

**A device must be able to take a new anchor**, and how is its application's (ADR-0011). A device
that can take an anchor only by cable is provisioned again at step 1.

---

## Consequences

**Every take-home Pi chooses its relationship with Deevnet**, and can change it.

**Under `deevnet`, the Pi's uptime depends on a visit a year**, or less with a longer leaf.

**Under `own`, the tenant is its own authority**, and its backup is what stands between a failed card
and re-anchoring every device.

**The kit grows**: `pki=`, a request and install path, a CA backup, a constraint on its own CA, and
dropping address names under `deevnet`.

---

## Alternatives considered

- **Rejected: every take-home Pi is managed by Deevnet.** Some owners never come back.
- **Rejected: every take-home Pi is independent.** The owner's own tenants would each carry a root.
- **Rejected: the Pi holds the tenant's Service CA** under `deevnet` (ADR-0039).

---

## Open questions

1. **Where does `own`'s CA key live** (§4)?
2. **A longer leaf, or a key backup, for `deevnet`** (§3)?
3. **Does `bring` take an issuing CA, or only leaves?**
4. **How is the choice made at a meetup**: a question when the card is written, or a later command?

---

## What would settle it

1. **An ESP32 dials an address and verifies a name** against a certificate with no address in it.
2. **A card under `deevnet`** is provisioned on the factory's network, runs a month away from it, and
   renews from a request carried on a USB stick.
3. **A card under `own` is lost**, and a new one restored from its backup serves the same devices
   without any device changing.
4. **A tenant moves from `deevnet` to `own`** with its service up throughout, and the old anchor is
   removed last.
