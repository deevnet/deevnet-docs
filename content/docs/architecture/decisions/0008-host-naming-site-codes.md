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

### D — Fixed-width site code prefix: `dv02hyp001p01`

Chosen. See below.

### A separate question: how wide are the other fields?

The four options above differ only in **where the site code sits**. Having settled that, the same
argument applies to every other field, and the answer is the same one: fix the width.

The alternative was to keep the existing variable-length grammar behind the site code —
`dv02-tenant-state-vm01` beside `dv02-ap01`, 22 characters against 9. That reads more easily in
isolation and needs no mnemonic table, but it gives up column alignment, makes the name unusable
as a fixed-layout key, and leaves the estate with names whose only shared structure is a prefix.

Compressing the role to a three-letter mnemonic and the form to a single letter is what buys the
fixed width. Both are lossless in the sense that matters: the hardware class moves from the form
code into the mnemonic, and the substrate — the one thing the mnemonic cannot carry, because
`core-rt01` is a VM and `core-rt02` is not — stays in a dedicated field.

---

## Decision

### The pattern

Every hostname is **thirteen characters**, and every field is fixed width. That is a property of
the scheme, not an outcome of the names that happen to exist.

```
dv{NN}{rrr}{sss}{f}{gg}

dv | 02 | hyp | 001 | p | 01
```

| Range | Field | Meaning |
|-------|-------|---------|
| `[0:2]` | `dv` | Constant. Marks the estate, and keeps the label from beginning with a digit |
| `[2:4]` | site | Two-digit site code |
| `[4:7]` | role | Three-letter mnemonic |
| `[7:10]` | sequence | `001`–`999`, restarting per role per site |
| `[10]` | form | `p` physical · `v` virtual · `e` embedded · `c` container |
| `[11:13]` | version | `01`–`99`, hardware generation of that instance |

Sequences restart per role per site, because the site code already carries the uniqueness. They are
allocated densely, with no gaps.

Because the widths are fixed and there is no separator, extracting a field is pure substring
slicing — no split step, and no dependence on how many separators a name happens to contain. The
`dv` prefix earns its two characters by keeping the label off a leading digit, which RFC 1123
permits but a good deal of tooling still mishandles.

**The form letter sits between the two digit runs deliberately.** Every field boundary except
`dv|02` is then a letter-to-digit transition, which the eye catches without knowing the widths.
The alternative — sequence and version adjacent, form last — puts a five-digit run with a
non-obvious 3+2 split at the centre of the name, where `dv02hyp00101p` gives a reader nothing to
tell them it is not sequence `010` version `1`.

`c` is reserved and unused: nothing is a first-class container host today, since PowerDNS and MinIO
run as podman services on VMs. The letter costs nothing now and is awkward to retrofit later.

Collapsing six physical form codes (`ph pi em rt sw ap`) into `p` moves the hardware class into the
mnemonic. That is a gain rather than a loss of information: naming.md §3.2 requires form codes to
"remain valid if the operating system or platform changes," and `p`/`v`/`e`/`c` is far more stable
against that than `hv` or `pi`.

### Role mnemonics

| Code | Class | | Code | Class |
|---|---|---|---|---|
| `hyp` | hypervisor | | `bld` | builder |
| `cor` | core router | | `tdn` | tenant DNS |
| `edg` | edge router | | `tst` | tenant state |
| `acc` | access switch | | `bgw` | bell gateway |
| `wap` | wireless AP | | `rpi` | Raspberry Pi |

This table is the part of the scheme that cannot be derived, which is why it lives in the record.

`cor`, `edg` and `acc` name **topological position** rather than device type, which is what
naming.md §3.3 asks of role prefixes on routing devices — "stable topological position rather than
software implementation." It also survives the awkward fact that `core-rt01` is a VyOS VM while
`core-rt02` is a physical appliance: `cor` is true of both, where a device-derived code would be
pulling in two directions. Device type lives in the form letter and in the host's own variables.

### The version field

The last two digits distinguish successive hardware behind the same logical instance, so a
replacement and the thing it replaces can exist **at the same time**:

```
dv00bld001p01   the box being replaced
dv00bld001p02   its replacement, running alongside it
```

Both sit in inventory, both get a VMID → MAC → reservation → A record, both resolve, and the two
generations sort adjacent.

**The rule: increment when old and new must coexist.** A physical box being replaced, or a VM
deliberately stood up as a separate instance for a migration. A plain rebuild does **not**
increment — the substrate's whole stateless principle is that a rebuilt host returns to the same
identity through the same VMID and MAC. Stating that line here is the point; without it, "do I bump
this?" gets answered differently every time it is asked.

This composes with the service CNAMEs the estate already publishes — `artifacts`, `pxe`, `tdns`,
`tfstate`, `pve`. A hardware refresh becomes: stand the new generation up beside the old, then
repoint one CNAME. Rolling back is the same move in reverse. That is what the naming standard's
"service names are not hostnames" rule was already reaching for; the version field is what makes
both ends nameable at once.

Two digits rather than one because embedded and IoT fleets turn over fastest — 999 instances and 99
generations per role per site.

**This is not a hypothetical.** `hv02` has already had its hardware swapped, recorded in
`ansible-inventory-deevnet` commit `775b503`, *"Set hv02 NIC MAC after hardware swap"*, where the
interface MAC moves from `UNKNOWN` to `54:bf:64:87:ca:eb`. The current naming had no way to express
it: the replacement silently inherited the name, and the only surviving trace is a commit message.
Under this scheme `hv02` arrives at generation `02` on its first day, which is the strongest
argument for the field that this record can make.

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
- **Names column-align.** A four-character prefix on every host — and, with the fields that follow
  also fixed, a thirteen-character name — makes lists and sorted output readable, and makes the
  site the primary sort key.
- **It scales to a hundred sites**, which is more than enough, and is trivially extended by digit
  count if it ever is not.
- **It leaves room for `00`** — a code for a host that belongs to no site, which the next section
  needs.

### The `provisioner` role becomes `bld`

`builder` is already the estate's word for this function: the inventory group is `builder`, the
collection is `deevnet.builder`, and the architecture page is *Builder & Core Services*. Only the
hostnames said `provisioner`. The mnemonic `bld` settles on the term everything else already uses,
rather than compressing an outlier.

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
dv00bld001p01
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
dv00bld001p01.home.deevnet.net    ->  10.10.99.95
dv00bld001p01.mobile.deevnet.net  ->  10.20.99.95
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

Every host is first-generation except `hv02`, which has already been replaced once.

| Current | New | |
|---------|-----|--|
| `core-rt01` | `dv02cor001v01` | the VyOS VM |
| `core-rt02` | `dv02cor002p01` | the physical Zima Board |
| `edge-rt01` | `dv02edg001p01` | |
| `access-sw01` | `dv02acc001p01` | |
| `ap01` | `dv02wap001p01` | |
| `hv01` | `dv02hyp001p01` | |
| `hv02` | `dv02hyp002p02` | **generation 02** — hardware already swapped |
| `pi01`–`pi04` | `dv02rpi001p01`–`dv02rpi004p01` | |
| `provisioner-vm02` | `dv02bld001v01` | |
| `provisioner-vm03` | `dv02bld002v01` | |
| `tenant-mgmt-vm01` | `dv02tdn001v01` | |
| `tenant-state-vm01` | `dv02tst001v01` | |
| `bellgw-em01` | `dv02bgw001e01` | the only `e` in the estate today |
| `provisioner-ph01` | `dv00bld001p01` | leaves the site |

The two core routers show the scheme doing real work: `cor001` and `cor002` are the first and
second core router, and the form letter — `v` for the VyOS VM, `p` for the Zima Board — records
which is which. Today only the arbitrary ordinal separates them.

**Home — `home.deevnet.net`, code `01`.** No hosts yet, so nothing is renamed; the shell is built
under the scheme directly, and would begin `dv01cor001p01`, `dv01acc001p01`, `dv01wap001p01`,
`dv01hyp001p01`.

Every name is thirteen characters, and the longest FQDN — `dv02hyp001p01.mobile.deevnet.net` — is
32, against a 63-character DNS label limit and a 64-character Linux hostname limit.

### Where the Raspberry Pis sit

`naming.md` §3.2 distinguishes `pi` ("full-size / primary Pi class") from `em` ("non-primary Pi:
Pi Zero, Arduino Q, Jetson"). With `e` available, the Pis take `p` — they are general-purpose
machines running a full OS, and `rpi` already carries the Pi-ness — leaving `bellgw-em01` as the
only `e`. The roadmap names `jetson-em01` and `console-pi05` as future hosts, which is where the
line will next be tested.

### The root name and secondary interfaces

The thirteen-character name is the host's **root name**, and it belongs to the host's primary
address. Additional addressed interfaces take the root name plus a dash plus an interface code:

```
dv02cor002p01        10.20.99.1     the primary
dv02cor002p01-wan    the upstream interface
```

A host with one NIC — every Pi, switch and access point today — has no suffixed name at all. This
is what the estate already does: exactly one interface per host carries `host_a_record: true` and
takes the bare name.

#### Interface codes

| Code | Interface |
|------|-----------|
| `-wan` | Wired upstream |
| `-wifi` | Wireless upstream |
| `-lan` | Downstream |
| `-stor` | Storage |
| `-tran` | Fabric transit |
| `-oob` | Lights-out / BMC |
| `-mgmt` | Management, **when it is not the primary** |

Allocated deliberately, like the role mnemonics. A new code is a conscious act rather than whatever
was typed into a variables file.

`-mgmt` is in the set but unused today. Under root-is-primary, a host whose primary interface is its
management interface already holds that address on the bare name. The code exists for the case where
the primary sits elsewhere — every Pi is `purpose: mgmt` on `segment: iot`, so a Pi that later
gained a management-segment NIC would need it.

#### Why the codes are curated rather than derived

Two fields already in the data model look like they could supply the suffix. Neither can.

**`purpose` collides.** `edge-rt01` has two interfaces with `purpose: wan` — the wired `eth-wan`
and `wifi`. Both would render `-wan`, and the DNS role reconciles aliases and records on name
alone, so which one survives is a function of ordering. That is the same defect class as the
`core-rt01`/`core-rt02` collision recorded below. The distinction that resolves it is the
**medium**, which `purpose` does not carry and never will, because both genuinely are WAN
interfaces. Nor is `purpose` constrained — `bellgw-em01` carries `purpose: web`.

**`segment` names nothing.** All seven secondary interfaces in the estate have no segment at all,
because a secondary interface is close to definitionally the one *outside* a segment. WAN sits
outside every segment; that is what makes it WAN.

Rendered against the seven interfaces that have no name today:

```
core-rt01  eth0     ->  dv02cor001v01-wan
core-rt02  eth1     ->  dv02cor002p01-wan
edge-rt01  eth1     ->  dv02edg001p01-lan
edge-rt01  eth-wan  ->  dv02edg001p01-wan
edge-rt01  wifi     ->  dv02edg001p01-wifi     <- purpose would have collided here
prov-ph01  eth1     ->  dv00bld001p01-tran
prov-ph01  wifi     ->  dv00bld001p01-wifi
```

#### Being named is not the same as being published

Six of those seven lease their address from upstream, and a leased address has no static record to
publish. The convention says what an interface **is called**; a record is published only where the
address is deterministic — a static assignment, or a MAC-keyed reservation, which is how every
substrate address already works. A WAN interface leasing from a hotel network has a name here and
no record in DNS.

This also means the convention is being written **ahead of need**: only `edge-rt01`'s second LAN
interface is statically addressed today. That is the right time to write it, because the home site
build and any storage segment make it real immediately, and because a convention invented under
pressure is a convention invented badly.

#### This supersedes two lines in the segmentation standard

[Network Segmentation](/docs/standards/network-segmentation/) §1 and §3 already mandate interface
suffixes — `-mgmt` for hosts on the management segment, `-stor` for hosts on the storage segment.
Nothing implements either, and the `-mgmt` rule contradicts root-is-primary as written: `hv01`'s
only NIC *is* its management interface, so a literal reading gives `hv01-mgmt` and no bare `hv01`.
The suffix belongs to the interface that is **not** the primary, and those two lines change with
the standard on acceptance.

#### The pipeline does not do this yet

Publishing per-interface records is not free. The DNS role reads only the **first** interface with
`host_a_record: true`, so a second addressed interface is invisible to it, and CNAMEs are harvested
from that same interface only. The bootstrap dnsmasq template suffixes an alias and its target with
the same domain, so a CNAME cannot cross zones either. None of that blocks the convention — it
blocks publishing, and it is work that comes with the first host that needs a second record.

### What the name deliberately does not carry

Many naming schemes put rack and position in the hostname. This one does not, and that is a
decision rather than an oversight.

**Placement is intent, not identity.** [Identity vs Intent](/docs/standards/identity-vs-intent/)
defines identity as "the stable, long-lived description of a system" and warns that mixing the two
makes "hostnames become lies." A rack position in the name means moving a device renames it, and a
rename cascades the full length of the chain this record depends on — declaration → MAC →
reservation → A record → OS hostname. The standard's only location language is *"Where does it live
(site)?"*, and the parenthetical scopes it to site, not to rack or position.

Its *Services Are Intent, Not Identity* section is the direct precedent: a host named `pi01` running
an SDR workload does not become `sdr-pi01` — the CNAME moves and the hostname does not. Placement is
the same shape of fact.

**The estate is heterogeneous by design.** Not everything is racked, and the platform pages already
say so: the access switch is *"Desktop or rack (1U)"*, the access point is *"Wall/pole mount"*. A
mandatory rack field forces a null value on the majority, and a field that is mostly placeholder
stops carrying information and starts carrying noise. One site is also literally mobile, where rack
position is meaningless.

**And the estate has rejected this shape of problem twice already** — the builder cannot carry a
site code because it roams between sites, hence `00`; and service names are kept separate from host
names precisely so a service can move. Placement is the same class: a property that changes
independently of the host's identity.

**The version field marks where the line sits.** Hardware generation *is* in the name, because it
changes only when the physical object is replaced — it is a fact about which object this is.
Placement changes without the object changing. That is the test for whether something belongs in a
name.

#### If placement is ever wanted

Aliases are the likely vehicle, since a stable *place* name pointing at whichever device currently
occupies it is the mirror image of the service alias the estate already runs, and it degrades
gracefully where a hostname field cannot — an unracked device simply has no alias, rather than
carrying a null rack. **No convention is proposed here**, deliberately: a sketch in a decision
record gets read as the decision.

Two things would need settling first, recorded so they are not rediscovered:

- **Inventory would be the source of truth, not DNS.** The estate declares once and generates
  everything else. A location alias hand-written into `cnames:` would put a fact only in DNS, where
  nothing else could read it and nothing would reconcile it. Placement belongs as an inventory
  field, with any alias generated from it the way A records and reservations already are.
- **An alias is a second thing that can be wrong**, and nothing reconciles it against physical
  reality. A stale location alias is worse than no location data, because it misleads during
  exactly the incident where someone is trying to find the box. The CNAME namespace also has no
  uniqueness guard today — see the defects below — which would need fixing first rather than being
  treated as a footnote.

[Inventory & Lifecycle Management](/docs/runbook/inventory-lifecycle/) already claims this
territory: asset tracking is in its scope, and it carries a five-stage lifecycle table that nothing
implements. That is where placement would land, not in a new home.

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
- **A hardware refresh becomes a CNAME repoint.** The version field lets a replacement and the
  thing it replaces hold distinct names, addresses and reservations at the same time, so the
  cutover is switching one service alias and the rollback is switching it back. `hv02` is proof the
  estate needed this before it had it.
- **Names column-align and slice.** Thirteen fixed characters means sorted output lines up, and any
  field is a substring at a known offset — no parsing, and nothing to break if a mnemonic ever
  contains an unexpected character.

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
- **A bare `dv02hyp001p01` needs the mapping known.** Fully qualified it is self-explanatory; in
  isolation it is not.
- **Legibility is the real price.** `dv02tdn001v01` tells a stranger far less than
  `tenant-mgmt-vm01` did, and the estate has no name-to-purpose lookup anywhere — no CMDB, no
  inventory report, nothing that answers "what is this?" from a name. That is precisely why the
  mnemonic table lives in this record rather than only in the standard, and why the field
  breakdown is written out rather than left implied. A scheme that needs a decoder ring and does
  not ship one is a worse trade than the variable-length names it replaced.
- **Ten mnemonics have to be learned**, and they are chosen by a person rather than derived, so
  they can be chosen badly. New classes need a code allocated deliberately, with the same care as
  a tenant index.
- **The name cannot answer "where is it".** Placement is excluded on purpose, but the consequence
  is that the question has no source of truth anywhere in the estate — not in the name, not in
  inventory, not in a CMDB. Finding a box is currently a matter of knowing. That is no worse than
  today, and it is worth stating that the scheme does not improve it.
- **Interface codes are a second curated vocabulary**, on top of the role mnemonics, with the same
  property: allocated by a person, so allocatable badly.

### No apex record is needed, and the site code does not imply one

"Belongs to no site" invites the reading that the builder wants an apex name,
`dv00bld001p01.deevnet.net`. It does not. Multi-homing it per zone, as above, already gives it
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
  authority. §3.1's `[role-]formNN` grammar is replaced outright; §3.2's eight form codes become
  the four-letter set, with the hardware classes they carried moving into the mnemonic table;
  §3.3's rules on when a role is optional no longer apply, because the mnemonic is mandatory and
  fixed width; and §6.1's combined-inventory option stops being a trap. Every example in the
  document changes.
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
- [Network Segmentation](/docs/standards/network-segmentation/) §1 and §3 lose their `-mgmt` and
  `-stor` interface-suffix rules, which this record supersedes — the suffix belongs to an interface
  that is not the primary, and §1's `hv01-mgmt` example says the opposite.
- [Inventory & Lifecycle Management](/docs/runbook/inventory-lifecycle/) is where placement would
  be taken up if it ever is. It already has the scope and none of the data model.
- Standing up the home site under the scheme first is the low-risk order: it has no hosts, so it
  proves the naming, the zone and the renamed directory before any of it reaches the running site.
