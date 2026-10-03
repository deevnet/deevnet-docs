---
title: "Trust and Identity"
weight: 7
---

# Trust and Identity

Every TLS connection on a Deevnet site verifies against one anchor, the **Deevnet Root CA**. The root
and each site's **Site CA** are held offline by a person, never by a system. Under each Site CA, two
**issuing CAs** separate the two kinds of identity a site has:

- **the substrate's servers**, issued by automation;
- **tenants' devices**, issued through the tenant interface as devices are registered.

The substrate never needs the second to build itself, and a tenant never touches the first.

New to certificates? The [Cryptography and PKI Primer](/docs/appendix/cryptography-and-pki-primer/)
explains keys, signatures, chains and CAs from the beginning.

---

**The hierarchy: Deevnet Root CA → Site CA → two issuing CAs**

{{< graphviz >}}
digraph pki {
    graph [
        rankdir=TB,
        nodesep=0.5,
        ranksep=0.45,
        fontname="Helvetica",
        bgcolor="#e0e0e0",
        pad=0.25,
        size="6.5,9!"
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

        root [label=<<b>Deevnet Root CA</b><br/><font point-size="10">one for the organization · 20 years</font>>, fillcolor="#f6e3c4", group=trunk]
        site [label=<<b>Site CA</b><br/><font point-size="10">one per site · 10 years</font>>, fillcolor="#f6e3c4", group=trunk]
    }

    split [shape=point, width=0.01, height=0.01, label="", group=trunk]

    subgraph cluster_online {
        label=<<b>Online: </b>at the site>
        labeljust=r
        labelloc=b
        fontname="Helvetica"
        fontsize=11
        style="dashed,rounded,filled"
        fillcolor="#eef3f8"
        color="#6b8aa8"
        margin=14

        sub [label=<<b>Substrate CA</b><br/><font point-size="10">site automation · 5 years</font>>, fillcolor="#e0f0ff"]
        dev [label=<<b>Tenant Device CA</b><br/><font point-size="10">secret store, via the tenant interface · 5 years</font>>, fillcolor="#d0e8d0"]
        { rank=same; sub; dev }
    }

    srv [label=<<b>serverAuth</b><br/><font point-size="10">hosts, appliances, services</font>>, shape=note, style=filled, fillcolor=white]
    cli [label=<<b>clientAuth</b><br/><font point-size="10">tenant devices (mTLS)</font>>, shape=note, style=filled, fillcolor=white]

    root -> site  [label="  What organization do I trust?", weight=10]
    site -> split [label="  Which Deevnet site owns this authority?", arrowhead=none, weight=10]
    split -> sub
    split -> dev
    sub -> srv    [label="  Who is this server?"]
    dev -> cli    [label="  Who is this device?"]
}
{{< /graphviz >}}

| Layer | Holds its key | Signs | Changes |
|---|---|---|---|
| Root CA | the operator, offline | Site CAs | once in twenty years |
| Site CA | the operator, offline | its site's issuing CAs | once in ten years |
| Substrate CA | the site's automation (its encrypted inventory) | every substrate server certificate | every five years |
| Tenant Device CA | the site's secret store | tenant devices' client certificates | every five years |

**For maximum integrity, the Root CA and every Site CA are generated and kept offline.** Whatever
holds a CA's key can mint anything under it. With the root and Site CA held offline, no compromise
of a site system, automation's included, can create a new CA. The worst a site loses is one issuing
CA, which the operator replaces in a short [ceremony](/docs/runbook/root-of-trust/) while every
client keeps trusting the root.

**One Deevnet Root CA serves every site; each site has its own Site CA under it.** An operator's
computer, a tenant's tooling or a device that works at more than one site trusts one anchor. A
site's own CA still bounds that site: a Site CA lost at one site is replaced without touching
another.

**Only a separate transfer medium crosses between the offline and online sides, and it never
carries a key.** The offline keys sit on media that never leaves the offline side. The transfer
medium carries a signing request in, under a manifest of hashes, and a signed certificate back,
under another.

Each side checks the manifest, refuses any private key on the medium, and checks the request or
certificate against what it expects. The online side checks the chain against its own copy of the
root. Tooling does the moving and the checking; the decision to sign is a person's.

---

## A private PKI, because a public CA cannot certify what a site serves

Every Deevnet certificate comes from Deevnet's own chain, not from a public CA such as Let's Encrypt
or a commercial one. A public CA could cover some of the site's names, but not the parts that matter
most:

- **Public CAs may not certify private addresses or internal names.** Since 2015 publicly trusted
  certificates cannot carry a reserved IP address or an internal name
  ([CA/Browser Forum](https://cabforum.org/working-groups/server/internal-names/)). A site's
  services are dialled at `10.20.x.x`, `127.0.0.1` and `localhost`.
- **Public CAs no longer issue client certificates.** Let's Encrypt removed TLS client authentication
  from its certificates in 2026, following browser root-program rules
  ([Let's Encrypt](https://letsencrypt.org/2025/05/14/ending-tls-client-authentication)). Device
  identity (mTLS) needs a CA that issues client certificates.
- **Public certificates cannot say what a certificate is for.** Let's Encrypt issues domain-validated
  certificates only, with no organization ([FAQ](https://letsencrypt.org/docs/faq/)), and the
  organizational unit is no longer permitted in any publicly trusted certificate
  ([Baseline Requirements](https://cabforum.org/working-groups/server/baseline-requirements/requirements/)
  §1.7.9). Deevnet's subjects carry O and OU so that *Issued To* and *Issued By* read plainly.
- **Public certificates are short-lived by rule, and renewal needs the internet.** Their maximum
  lifetime is 200 days from March 2026, 100 from 2027 and 47 from 2029 (Baseline Requirements §6.3.2).
  Each renewal needs the CA reachable, and a mobile site runs without internet access.
- **Public certificates publish their names.** Every certificate goes to public Certificate
  Transparency logs, where crawlers find it ([FAQ](https://letsencrypt.org/docs/faq/)). Every host,
  service and tenant name on the site would be listed there.

A paid CA changes none of these: the rules are the CA/Browser Forum's, and every publicly trusted CA
follows them. A private PKI's one cost is that nothing trusts its root by default, so the root is
installed where it is needed ([below](#where-the-deevnet-root-ca-is-trusted)). Nothing Deevnet serves is
meant for the public internet, so that is a cost only Deevnet's own machines, tenants and operators
pay.

## Substrate certificates come from automation, never from the secret store

The substrate is built in order: the network, the hypervisors, then the service VMs, one of which
runs the secret store. Each step needs certificates for the steps before it. If those came from the
secret store, a site rebuilt from nothing would wait on itself.

So **every substrate certificate comes from the Substrate CA, issued by automation** on the control
node. That covers every bare-metal host, appliance and service VM, and the services on them, the
secret store's own interface included. The Substrate CA's key lives where automation's other secrets
do. The secret store issues nothing the substrate needs.

---

## Server identity and device identity come from separate CAs

Every edge device belongs to a tenant
([ADR-0032](/docs/architecture/decisions/edge-devices/0032-every-device-belongs-to-a-tenant/)), so device
identity is always a tenant's: the tenant is named in every device certificate.

| | Substrate server | Tenant device |
|---|---|---|
| Proves | "I am this host or service" | "I am this tenant's device" |
| Issued by | Substrate CA | Tenant Device CA |
| Named by | DNS names and addresses, from the inventory | a URI naming site, tenant and device |
| Used for | server authentication only | client authentication only |
| Its key is made | by automation, for the server | on the device, never inside the substrate |

A certificate is one or the other, never both. A service that accepts devices trusts only the Tenant
Device CA for its clients, so a stolen server certificate cannot log in as a device, and a device
certificate cannot impersonate a service.

---

## Tenant devices will prove their identity with client certificates (mTLS)

This is the target for tenant devices; today they authenticate to the message broker with a username
and password over TLS ([ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §8).

1. **The device makes its own key and signing request.** A device that cannot do so has the
   tenant's own computer make them. The tenant submits the request through the tenant interface, for
   a device the tenant has registered.
2. **The Tenant Device CA signs it, for a registered device only.** The platform checks the request
   names that tenant's registered device. The certificate is valid one year, for client
   authentication only, with the identity `urn:deevnet:<site>:tenant:<tenant>:device:<device>`. It
   goes back to the tenant; the key never left the device.
3. **Device and service each present a certificate.** For example, at the message broker:
   - the service shows its substrate server certificate, and the device checks it against the
     Deevnet Root CA;
   - the device shows its client certificate, and the service checks it against the Tenant Device
     CA.
4. **The service authorizes the device by the identity in its certificate.** It applies that
   device's permissions: its tenant's topics, and nothing else.
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
| The operator's computer | installed by hand, once |

---

## The rules are in the Certificates standard

The certificates themselves (subjects, names, keys, lifetimes, where each key may live) are set by
the [Certificates standard](/docs/standards/certificates/). The decision and its alternatives are
[ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/).
