---
title: "ADR-0008: Host Naming and Site Codes"
weight: 8
---

# ADR-0008: Host Naming and Site Codes

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-04 |
| **Scope** | How a host is named, and how a site is identified in that name and in DNS |
| **Related** | [ADR-0002: Tenant Fabric Numbering](/docs/architecture/decisions/0002-tenant-fabric-numbering/) — the site octet this record's site codes sit alongside |

---

## Context

Only the mobile site has hosts. Its names — `hv01`, `core-rt01`, `provisioner-ph01` — are scoped to
their site by inventory boundary alone, and the home site's shell would reuse every one of them.

Nothing breaks today. Each site has its own inventory, its own resolver and its own DHCP server,
and a bare `hv01` resolves through a site-scoped search domain. The
[Naming Standard](/docs/standards/naming/) §3.1 says as much — hostnames are unique "within a site
zone" — and never claims more.

The question is whether that is the right scope, and it is worth asking now for a reason that has
nothing to do with elegance: **the short name is the identity that leaves the estate.**

### The short name is the wire identity, everywhere

`deevnet_fqdn` is referenced in exactly one place in the entire estate — `powerdns_apex_ns`, where
an NS record cannot point at a CNAME. `ansible_fqdn`, `ansible_hostname` and
`inventory_hostname_short` appear nowhere at all. Every other identity is the bare short name:

| What | Value |
|------|-------|
| OS hostname, every Fedora host | `inventory_hostname` |
| OS hostname, Proxmox bare metal | the short name; the FQDN appears only in `/etc/hosts` |
| Proxmox VM name | `inventory_hostname` |
| Container hostnames | `inventory_hostname` |

So the name a host announces itself by — to a syslog collector, a metrics scrape, a backup
catalogue, a restored VM on another node — is `hv01`, with no site in it. Two sites running the
same automation would produce two hosts that are indistinguishable on the wire.

### Three things make now the cheapest moment

**Nothing parses the hostname grammar.** No code anywhere splits a name into role, form and
ordinal. Every `regex_replace` in the estate operates on IP addresses, MAC addresses, artifact
names or NetworkManager output. The shape of a hostname is a pure convention choice, unconstrained
by code — which will stop being true the first time something parses one.

**There is no monitoring yet.** The logging and monitoring plays in the management collection's
`site.yml` are still commented-out placeholders. There are zero metric labels, log source names or
dashboard keys in existence, so there is no historical series to break. Whatever a metrics stack
adopts as its `instance` label, it will adopt on the day it is built.

**Identity is MAC-anchored, not name-anchored.** DNS records and DHCP reservations are generated
from inventory and reconciled on MAC addresses that a rename does not touch, so most of the runtime
follows a rename by itself. The measured cost of renaming the mobile site is roughly 124 references
across inventory and code and 157 across documentation — plus the OS hostname on 17 live machines,
which is the only genuinely manual part.

### A contradiction the current standard already carries

[Naming Standard](/docs/standards/naming/) §6.1 permits two ways to express site membership:
separate inventories per site, **or** a combined inventory with explicit `dvnt` / `dvntm` site
groups.

The second is impossible with duplicate short names. Ansible merges two same-named hosts into one
host object, last-source-wins, with no warning — so a combined inventory would not error, it would
silently halve. The standard offers an option the naming scheme forbids.

That is not hypothetical harm today, because nothing combines them. It is a latent instruction to
do something that would fail quietly.

---

## Options considered

### A — Leading full site name: `dvntm-hv01`

Most self-evident, and matches the common enterprise habit of ordering a name from largest scope to
smallest. It fails on a detail specific to these two site names:

**`dvnt` is a strict prefix of `dvntm`.**

```
glob  dvnt*    matches BOTH sites
glob  dvnt-*   matches home only
regex ^dvnt    matches BOTH sites
regex ^dvnt-   matches home only
```

Correctness then depends on every consumer remembering the hyphen — in a metrics relabel rule, a
firewall alias, a host group, an `--limit` pattern. A rule scoped to `dvnt*` silently swallows the
other site, and silently is the operative word: the query succeeds and returns too much.

This is fixable by choosing a site token where neither value is a prefix of another, which is what
the accepted option does.

### B — Trailing full site name: `hv01-dvntm`

Inverts the hazard: `-dvnt$` does not match `-dvntm`, so anchored suffix matching is safe. Keeps
function-first sorting and tab completion. Rejected for two smaller reasons — location-last is
unconventional enough to surprise, and the ordinal stops being the terminal element of the name,
which is the one structural assumption a future parser is most likely to make.

### C — Site digit folded into the ordinal: `hv201`

Shortest of the four, no stutter against the site zone, and no prefix relationship between sites.
It is also the most consistent with how the estate already identifies a site — by number, in the
subnet's second octet, the MAC namespace `02:de:{octet}`, the BGP ASN and the VNI bases.

Rejected on legibility: `hv201` cannot be read without knowing the convention, and the failure mode
of a half-remembered convention is misreading a hostname rather than failing to match one. It also
invites deriving the digit from `deevnet_site_octet`, which would make the hostname a function of
the IP plan — renumber a site and every host is renamed.

### D — Fixed-width site code prefix: `dv02-hv01`

Chosen. See below.

---

## Decision

### The pattern

```
dv{NN}-[role-]{form}{nn}
```

| Field | Meaning |
|-------|---------|
| `dv` | Constant. Marks the estate, and keeps the label from beginning with a digit |
| `{NN}` | Two-digit site code |
| `[role-]` | Optional role, unchanged from the existing grammar |
| `{form}` | Form code — `hv vm ph pi em rt sw ap`, unchanged |
| `{nn}` | Two-digit ordinal, restarting per site |

Ordinals restart per site because the site code already carries the uniqueness. Nothing renumbers.

### Site codes

| Code | Site | Zone |
|------|------|------|
| `00` | No site — the roaming builder appliance | resolved in whichever site zone it is attached to |
| `01` | Home, formerly `dvnt` | `home.deevnet.net` |
| `02` | Mobile, formerly `dvntm` | `mobile.deevnet.net` |

The site zones are renamed with the hosts. `dvnt` and `dvntm` were opaque and, being prefixes of
one another, awkward to match on; `home` and `mobile` say what the site is. Inventory directories
follow, becoming `home/` and `mobile/`, so the directory, the zone and the `deevnet_substrate`
value agree.

Note that the hostname and the zone deliberately carry *different* site tokens — `dv02` and
`mobile`. That removes the stutter a leading site name would produce
(`dvntm-hv01.dvntm.deevnet.net`), at the cost of two vocabularies for one concept. In fully
qualified form each explains the other; in bare form the numeric code needs the mapping known.

### Why a fixed-width numeric code

- **No site code is a prefix of another.** `dv01` and `dv02` are the same length, so option A's
  glob hazard cannot occur regardless of how carefully a pattern is written.
- **Names column-align.** A five-character prefix on every host makes lists and sorted output
  readable, and makes the site the primary sort key.
- **It scales to a hundred sites**, which is more than enough, and is trivially extended by digit
  count if it ever is not.
- **It leaves room for `00`** — a code for a host that belongs to no site, which the next section
  needs.

### The `provisioner` role becomes `builder`

`builder` is already the estate's word for this function: the inventory group is `builder`, the
collection is `deevnet.builder`, and the architecture page is *Builder & Core Services*. Only the
hostnames said `provisioner`. Renaming them removes the last holdout rather than introducing a new
term.

### The builder is site `00`

The documentation has said two things about the builder. The
[authority transition gap analysis](/docs/runbook/authority-transition-gap-analysis/) describes one
physical appliance that plugs into one site's management VLAN at a time, with its address per site
defined in that site's inventory. The
[home site roadmap](/docs/roadmap/infrastructure/dvnt/builder/) describes a permanent, always-on
provisioning node dedicated to the home site.

This record settles it in favour of the roaming appliance, and site code `00` is what makes that
expressible. A host that moves between sites cannot honestly carry either site's code; `00` says
it belongs to none.

```
dv00-builder-ph01
  one physical box, one hardware identity
  listed in BOTH site inventories
  env at home   ->  10.10.99.95
  env at mobile ->  10.20.99.95
```

It is listed in both inventories rather than an inventory of its own because the bootstrap role
generates a site's DHCP, DNS and PXE configuration from `groups['all']` — the builder has to see
the hosts it is building. This is the split the
[Identity vs Intent](/docs/standards/identity-vs-intent/) standard already describes, made
concrete: the `infrastructure:` block is hardware identity and is substrate-agnostic, the `env:`
block is the environment binding and is per-site.

In DNS it is therefore **multi-homed**, in the sense
[Builder & Core Services](/docs/architecture/builder/) already gives that word: one entry per site
zone, each resolving to the address the box has at that site.

```
dv00-builder-ph01.home.deevnet.net    ->  10.10.99.95
dv00-builder-ph01.mobile.deevnet.net  ->  10.20.99.95
```

Two fully qualified names, each with exactly one address. That page reached the same conclusion by
a different route — it published *interface-specific identities* (`provisioner-01-dvnt`,
`provisioner-01-dvntm`) precisely to avoid "ambiguous multi-A records." This record keeps its
principle and improves its mechanism: the disambiguation moves out of the short name and into the
zone, so one box keeps one identity instead of acquiring a name per site.

Multi-A on a single name would be the wrong reading of "multi-homed" here. The appliance is at one
site at a time by design, so an RRset holding both addresses would send half of all connections to
an address where nothing is listening — a timeout rather than an error, which is the worse failure.

### The rename

**Mobile — `mobile.deevnet.net`, code `02`**

| Current | New |
|---------|-----|
| `edge-rt01` | `dv02-edge-rt01` |
| `core-rt01` | `dv02-core-rt01` |
| `core-rt02` | `dv02-core-rt02` |
| `access-sw01` | `dv02-access-sw01` |
| `ap01` | `dv02-ap01` |
| `hv01` | `dv02-hv01` |
| `hv02` | `dv02-hv02` |
| `pi01`–`pi04` | `dv02-pi01`–`dv02-pi04` |
| `provisioner-vm02` | `dv02-builder-vm02` |
| `provisioner-vm03` | `dv02-builder-vm03` |
| `tenant-mgmt-vm01` | `dv02-tenant-mgmt-vm01` |
| `tenant-state-vm01` | `dv02-tenant-state-vm01` |
| `bellgw-em01` | `dv02-bellgw-em01` |
| `provisioner-ph01` | `dv00-builder-ph01` — leaves the site |

**Home — `home.deevnet.net`, code `01`.** No hosts yet; the shell is built under the scheme
directly, so nothing is renamed there.

The longest resulting name is `dv02-tenant-state-vm01` at 22 characters, and the longest FQDN
`dv02-tenant-state-vm01.mobile.deevnet.net` at 41 — against a 63-character DNS label limit and a
64-character Linux hostname limit. Length is not a constraint.

---

## Consequences

### Positive

- **A name is unambiguous wherever it appears** — in a log line, a metric label, a restored VM, a
  conversation — without depending on which inventory was loaded.
- **The prefix hazard is designed out** rather than mitigated by discipline. A fixed-width code
  cannot be a prefix of another.
- **A host that belongs to no site can say so.** `00` is not a workaround; it is the honest answer
  for an appliance that moves.
- **`builder` becomes consistent** across group, collection, role name and documentation.
- **The combined-inventory option in the standard becomes real.** With globally unique names,
  §6.1's second method stops being a trap.

### Negative

- **Every mobile host is renamed**, at roughly 124 references across inventory and code and 157
  across documentation, plus the OS hostname on 17 live machines. DNS records and DHCP reservations
  regenerate from unchanged MACs, so the runtime largely follows; the OS hostnames do not.
- **`home` and `mobile` describe deployment context, not identity.** The
  [Identity vs Intent](/docs/standards/identity-vs-intent/) standard says identity "does not change
  simply because software or workloads change," and the
  [Naming Standard](/docs/standards/naming/) §1 calls site names "environment identifiers, not
  workloads." If the mobile site is ever permanently docked, or a second site is also at home,
  `mobile` becomes a lie in a way `dvntm` could not. The `dv{NN}` code is opaque and immune to
  this; only the zone carries a label that can age. Accepted deliberately, for readability, and
  recorded here so the trade is visible if it ever has to be revisited.
- **Two vocabularies for "site"** — the numeric code in the hostname, the word in the zone, on top
  of the site octet that already exists in addressing.
- **A bare `dv02-hv01` needs the mapping known.** Fully qualified it is self-explanatory; in
  isolation it is not.

### No apex record is needed, and the site code does not imply one

"Belongs to no site" invites the reading that the builder wants an apex name,
`dv00-builder-ph01.deevnet.net`. It does not. Multi-homing it per zone, as above, already gives it
a correct name everywhere it is reachable, and each of those names is unambiguous. The site code
describes the *box* — a machine with no home site — not the zone its records live in.

If an apex name is ever wanted anyway, the cost is not uniform, and it depends on which authority
is serving at the time:

- **While building a site the builder is its own DNS authority.** In bootstrap-authoritative mode
  it runs dnsmasq and answers for the site zone itself, before the core router exists. dnsmasq
  assembles each record's fully qualified name on its own line
  (`address=/<name>.<domain>/<ip>`), so publishing a differently-domained record there costs one
  template line. In the mode where the builder most needs to be findable by a name that does not
  depend on the site, it is already free to publish one.
- **In router-authoritative steady state it is not free.** The Unbound API takes hostname and
  domain as separate fields, and the DNS role's reconciliation maps are keyed on hostname alone —
  which is also why a name appearing in two zones on one resolver would collapse to a single map
  entry. Supporting a per-record zone means re-keying those maps on `(hostname, domain)`, which is
  a real change to the role's idempotency, not a template line.

So the recommendation stands — publish per site zone, add no apex record — but the reason is that
multi-homing makes it unnecessary, not that the role makes it hard.

### Defects this investigation surfaced

All four predate this decision and are consequences of the same confusion — treating a short name
as if it were a namespace. They need fixing whenever this is executed, and three of them are live
now:

- **Both core routers claim the same service names.** `core-rt01` and `core-rt02` each declare
  `gateway`, `dns` and `dhcp` as CNAMEs in one zone. The DNS role categorises aliases by name
  alone, so which host wins is a function of ordering. A live collision, inside one site, with no
  guard — and evidence that the pipeline has no collision detection to extend across sites.
- **The DNS role's default domain is a site literal.** `dns_domain` defaults to
  `dvntm.deevnet.net` inside the shared role, overridden only in the mobile inventory. The home
  inventory has no `routers/` group vars at all, so running DNS against home today would publish
  home's hosts into the mobile zone.
- **Both sites allocate management VMIDs from `200-299`,** and the Proxmox VM name is the short
  name. Two of the three axes of VM identity — VMID, name, MAC — would collide between sites;
  only the MAC namespace `02:de:{octet}` keeps them apart. The VMID audit answers "is this VMID
  mine?" by string-comparing the Proxmox name to `inventory_hostname`.
- **No uniqueness assertion exists anywhere,** in either scope. Nothing would have caught any of
  the above.

---

## What follows acceptance

This record is `Proposed`. Nothing changes while it stands here — not the inventories, not the
collections, not the standards. On acceptance:

- The [Naming Standard](/docs/standards/naming/) is the first thing to change, since it is the
  authority. §3.1's grammar gains the site code; §6.1's combined-inventory option stops being a
  trap and its examples stop saying `provisioner-ph01`.
- The site tables in [Addressing](/docs/architecture/addressing/) and the
  [Architecture index](/docs/architecture/), and the site names in
  [ADR-0002](/docs/architecture/decisions/0002-tenant-fabric-numbering/), follow.
- The tenant registry's zone pattern `<tenant>.<site>.deevnet.net` resolves to
  `<tenant>.mobile.deevnet.net`. Destroying the demo tenant first — it is already marked for
  destruction after verification — leaves no live tenant zone to migrate.
- [Builder & Core Services](/docs/architecture/builder/) §"Multi-Homing Without Identity Confusion"
  keeps its principle but loses its mechanism. Its `provisioner-01-dvnt` /
  `provisioner-01-dvntm` example put the site in the short name and is doubly out of date — it also
  uses the retired `mgmt.deevnet.net` zone. Replace the example with the per-zone form; the
  paragraph's reasoning about ambiguous multi-A records is still exactly right and should stay.
- Standing up the home site under the scheme first is the low-risk order: it has no hosts, so it
  proves the naming, the zone and the renamed directory before any of it reaches the running site.
