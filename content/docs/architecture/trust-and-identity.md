---
title: "Trust and Identity"
weight: 7
---

# Trust and Identity

Deevnet runs its own **private PKI**: every certificate on a Deevnet site comes from Deevnet's own
certificate authorities, and is trusted only where Deevnet has installed its root. Every TLS
connection verifies against that one anchor, the **Deevnet Root CA**. The root and each site's
**Site CA** are held offline by a person, never by a system. Below them, **issuing CAs** separate the
kinds of identity there are:

- each site's **Substrate CA** issues that site's own server certificates, through automation;
- the Mobile Factory's **Tenant Service CA** issues server certificates for tenants' own services,
  through the tenant interface, for names in the tenant's own space
  ([ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/));
- the Mobile Factory's **Tenant Device CA** is the issuer for tenants' device certificates
  ([ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/) §3); it has issued none yet.

**The two tenant CAs are the Mobile Factory's, and serve tenants at every site**
([ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/)). Only
the factory creates tenants, so another site has a Site CA and a Substrate CA for its own
infrastructure, and nothing for tenants. The substrate builds itself without either tenant CA, and
no tenant ever touches a Substrate CA.

Deevnet uses a private PKI because a public CA cannot certify what a site serves: private addresses,
internal names, and device client certificates. The comparison with Let's Encrypt and commercial CAs
is in [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/#alternatives-considered).

New to certificates? The [Cryptography and PKI Primer](/docs/appendix/cryptography-and-pki-primer/)
explains keys, signatures, chains and CAs from the beginning.

---

**The hierarchy: Deevnet Root CA → a Site CA per site → each site's Substrate CA, and the Mobile
Factory's two tenant CAs**

{{< graphviz >}}
digraph pki {
    graph [
        rankdir=TB,
        nodesep=0.45,
        ranksep=0.45,
        fontname="Helvetica",
        bgcolor="#e0e0e0",
        pad=0.25,
        size="7,9!"
    ]
    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=13, margin="0.25,0.12", penwidth=1.2]
    edge [arrowsize=0.7, fontname="Helvetica", fontsize=11, fontcolor="#333333", color="#555555"]

    subgraph cluster_offline {
        label=<<b>Offline: </b>held by the operator, never on a network>
        labeljust=l
        fontname="Helvetica"
        fontsize=11
        style="dashed,rounded,filled"
        fillcolor="#f5ead8"
        color="#a0855b"
        margin=14

        root [label=<<b>Deevnet Root CA</b><br/><font point-size="10">one for the organization · 20 years</font>>, fillcolor="#f6e3c4"]
        msite [label=<<b>Mobile Site CA</b><br/><font point-size="10">the Mobile Factory · 10 years</font>>, fillcolor="#f6e3c4"]
        osite [label=<<b>Site CA</b><br/><font point-size="10">any other site · 10 years</font>>, fillcolor="#f6e3c4", style="rounded,filled,dashed"]
        { rank=same; msite; osite }
    }

    subgraph cluster_online {
        label=<<b>Online: </b>keys held in the vault>
        labeljust=r
        labelloc=b
        fontname="Helvetica"
        fontsize=11
        style="dashed,rounded,filled"
        fillcolor="#eef3f8"
        color="#6b8aa8"
        margin=14

        msub [label=<<b>Mobile Substrate CA</b><br/><font point-size="10">the factory's automation · 5 years</font>>, fillcolor="#e0f0ff"]
        svc [label=<<b>Tenant Service CA</b><br/><font point-size="10">secret store, via the tenant interface · 5 years</font>>, fillcolor="#d0e8d0"]
        dev [label=<<b>Tenant Device CA</b><br/><font point-size="10">secret store, via the tenant interface · 5 years</font>>, fillcolor="#d0e8d0"]
        osub [label=<<b>Substrate CA</b><br/><font point-size="10">that site's automation · 5 years</font>>, fillcolor="#e0f0ff", style="rounded,filled,dashed"]
        { rank=same; msub; svc; dev; osub }
    }

    srv [label=<<b>serverAuth</b><br/><font point-size="10">a site's hosts,<br/>appliances, services</font>>, shape=note, style=filled, fillcolor=white]
    tsv [label=<<b>serverAuth</b><br/><font point-size="10">tenants' own services,<br/>at every site</font>>, shape=note, style=filled, fillcolor=white]
    cli [label=<<b>clientAuth</b><br/><font point-size="10">tenant devices (mTLS),<br/>at every site</font>>, shape=note, style=filled, fillcolor=white]

    root -> msite [label="  Which site owns this authority?"]
    root -> osite
    msite -> msub
    msite -> svc
    msite -> dev
    osite -> osub
    msub -> srv   [label="  Who is this server?"]
    osub -> srv
    svc -> tsv    [label="  Whose service is this?"]
    dev -> cli    [label="  Who is this device?"]
}
{{< /graphviz >}}

**For maximum integrity, the Root CA and every Site CA are generated and kept offline.** Whatever
holds a CA's key can mint anything under it. With the root and Site CA held offline, no compromise
of a site system, automation's included, can create a new CA. The worst a site loses is one issuing
CA, which the operator replaces in a short [ceremony](/docs/runbook/root-of-trust/) while every
client keeps trusting the root.

**Everything under a Site CA can vouch only for Deevnet's own names and private addresses.** Each
Site CA is name-constrained to `deevnet.net`, `localhost` and private and loopback address ranges, so
even a leaked key below it cannot make a certificate a computer trusting the Deevnet Root CA would
accept for a public site.

**One Deevnet Root CA serves every site; each site has its own Site CA under it.** An operator's
computer, a tenant's tooling or a device that works at more than one site trusts one anchor. A
site's own CA still bounds that site's infrastructure: a Site CA lost at one site is replaced
without touching another's. The Mobile Site CA also stands over the tenant CAs, so replacing it
reaches every tenant, wherever it runs.

**Only a separate transfer medium crosses between the offline and online sides, and it never
carries a key.** The offline keys sit on media that never leaves the offline side. The transfer
medium carries a signing request in, under a manifest of hashes, and a signed certificate back,
under another.

Each side checks the manifest, refuses any private key on the medium, and checks the request or
certificate against what it expects. The online side checks the chain against its own copy of the
root. Tooling does the moving and the checking; the decision to sign is a person's.

---

## Substrate certificates come from automation, never from the secret store

The substrate is built in order: the network, the hypervisors, then the service VMs, one of which
runs the secret store. Each step needs certificates for the steps before it. If those came from the
secret store, a site rebuilt from nothing would wait on itself.

So **every substrate certificate comes from the Substrate CA, issued by automation** on the control
node. That covers every bare-metal host, appliance and service VM, and the services on them, the
secret store's own interface included. The Substrate CA's key lives where automation's other secrets
do. The secret store issues nothing the substrate needs.

---

## Tenant CA keys come from the vault, never from the secret store

**Every key the secret store uses is made outside it, held in the vault, and imported**
([ADR-0042](/docs/architecture/decisions/substrate/0042-openbao-sealed-outside-work-sessions/) §4,
[CHG-0036](/docs/changes/2026/0036-openbao-keys-from-the-vault/)). Automation makes each tenant CA's
key and its signing request; the offline Site CA signs the request in a ceremony; automation imports
the key and the certificate into the secret store together. The secret store never makes a CA key
of its own, and the key it holds is a copy.

**A lost secret store is rebuilt, not restored.** A rebuilt one imports the same keys from the vault,
so every certificate a tenant CA issued still verifies, and every secret it sealed still opens.

**Today the secret store opens itself on start.** Keeping it sealed outside a work session, opened by
an operator to create a tenant or issue a certificate, is decided but not built
([CHG-0053](/docs/changes/2026/0053-openbao-shamir-seal/)).

---

## Server identity and device identity come from separate CAs

Every edge device belongs to a tenant
([ADR-0032](/docs/architecture/decisions/edge-devices/0032-every-device-belongs-to-a-tenant/)), so device
identity is always a tenant's: the tenant is named in every device certificate.

| | Substrate server | Tenant device | Tenant service |
|---|---|---|---|
| Proves | "I am this host or service" | "I am this tenant's device" | "I am the service at this name in this tenant's zone" |
| Issued by | Substrate CA | Tenant Device CA | Tenant Service CA |
| Named by | DNS names and addresses, from the inventory | a URI naming tenant and device, with no site | its site-less name, then a name at each site asked for, built by the Deevnet API from labels |
| Used for | server authentication only | client authentication only | server authentication only |
| Its key is made | by automation, for the server | on the device, never inside the substrate | by the tenant, never inside the substrate |

**A tenant's service is a server, and is still not the substrate's.** Its certificate comes from a
CA of its own, so a tenant never holds a key certified by the CA that identifies the substrate. The
API reads a tenant's signing request for its public key alone, and builds every name from a label and
the tenant's name: the site-less name `<label>.<tenant>.deevnet.net` as the common name and first
SAN, then `<label>.<tenant>.<site>.deevnet.net` for each site the request names, among those the
site issues for
([ADR-0040](/docs/architecture/decisions/naming-and-dns/0040-tenant-names-without-a-site/) §3). A
tenant cannot ask for a name that is not its own.

**The API's reserved names are what keep a tenant's names apart from a site's.** A site-less tenant
name, `console.eds.deevnet.net`, and a site's substrate name, `grafana.mobile.deevnet.net`, have the
same shape, two labels under `deevnet.net`. The secret store's signing role allows any name at least
two labels under `deevnet.net`, so it refuses a name outside it, but it cannot tell a tenant from a
site. The API can: it refuses a tenant named after a site, a site code, a global alias or `mqtt`, and
the label `device`, which holds a tenant's device names. Until the secret store has a signing role
per tenant, that check is the API's alone.

**A Deevnet Pi serves its tenant with a Tenant Service CA certificate**
([ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/) §2). The
Pi makes its key and a signing request; the Mobile Factory has it signed for the tenant's names and
the sites the Pi will answer at; the Pi installs the certificate with the Deevnet Root. Its own
services then dial its names, mapped to the Pi itself, so the certificate needs no `localhost` and no
address. Until a certificate is installed, a card serves with a CA of its own that only it holds.

A certificate is a server's or a client's, never both. A service that accepts devices trusts only the Tenant
Device CA for its clients, so a stolen server certificate cannot log in as a device, and a device
certificate cannot impersonate a service.

---

## Tenant devices will prove their identity with client certificates (mTLS)

**Today tenant devices log in to the message broker with a username and password over TLS**
([ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §8), and check the
broker against the Deevnet Root. Client certificates are the target, not yet built
([CHG-0034](/docs/changes/2026/0034-device-certificates/)):

1. **The device makes its own key and signing request.** A device that cannot do so has the
   tenant's own computer make them. The tenant submits the request through the tenant interface, for
   a device the tenant has registered.
2. **The Tenant Device CA signs it, for a registered device only.** The platform checks the request
   names that tenant's registered device. The certificate is valid one year, for client
   authentication only, with the identity `urn:deevnet:tenant:<tenant>:device:<device>`, which names
   no site, so a device that moves keeps it
   ([ADR-0039](/docs/architecture/decisions/substrate/0039-factory-tenant-cas-serve-every-site/) §4).
   It goes back to the tenant; the key never left the device.
3. **Device and service each present a certificate.** For example, at the message broker:
   - the broker shows its server certificate, a site broker's from its Substrate CA or a Deevnet
     Pi's from the Tenant Service CA, and the device checks it against the Deevnet Root CA;
   - the device shows its client certificate, and the service checks it against the Tenant Device
     CA.
4. **The service authorizes the device by its registration at that site.** The identity in the
   certificate must name a device registered there, and its key must match the one recorded when
   the certificate was issued. It applies that device's permissions: its tenant's topics, and
   nothing else. Registration is a device's visa; its certificate is its passport.
5. **The device renews yearly**, by repeating steps 1 and 2 with a new request before the year runs
   out.
6. **Deregistering a lost or retired device revokes it at once.** The platform stops authorizing its
   identity, whatever its certificate says.

What crosses the substrate–tenant boundary is a signing request in and a certificate out. Device
keys, and the firmware-signing keys that are the tenant's alone
([ADR-0011](/docs/architecture/decisions/edge-devices/0011-edge-devices-application-owned/) §4),
never do.

---

## Where the Deevnet Root CA is trusted

| Where | How |
|---|---|
| Every substrate host and VM, and the images they are built from | the operating system's trust store, laid down by the build |
| Each service | the root beside its own certificate, for the clients it calls |
| Tenants' tooling and devices | delivered with their credentials, checked by fingerprint |
| A Deevnet Pi | installed with its certificate, for every service on it |
| The operator's computer | installed by hand, once |

---

## The rules are in the Certificates standard

The certificates themselves (subjects, names, keys, lifetimes, where each key may live) are set by
the [Certificates standard](/docs/standards/certificates/). The decision and its alternatives are
[ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/).
