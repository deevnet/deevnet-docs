---
title: "Cryptography and PKI Primer"
weight: 1
---

# Cryptography and PKI Primer

Every secure connection solves the same problem: talking privately to a machine you have never met,
over a network that anyone along the way can read and alter. Encryption hides the conversation, but
it can't tell you *who* is on the other end. That is the job of a **public key infrastructure
(PKI)**: certificates that bind names to keys, signed by **certificate authorities (CAs)** that you
decided to trust ahead of time. The protocol that puts it all to work on a connection is **TLS**,
the "S" in HTTPS. This page builds TLS and PKI up one idea at a time, with no math. It ends with why
the web's PKI is invisible to almost everyone, and why a private network like Deevnet runs its own.

The boxes marked *Try it* are optional. They show the same ideas on a real website, using a browser
or `openssl`.

---

## TLS is the layer that makes an ordinary connection secure

**TLS (Transport Layer Security) wraps a network connection so that nobody along the way can read it
or change it.** It sits between the connection itself (TCP) and the application using it, and the
application barely notices. HTTPS is plain HTTP carried inside TLS. Secure email, MQTT for devices,
database clients and most other modern protocols do the same. When a browser shows a padlock, the
page came over TLS.

{{< graphviz >}}
digraph stack {
    graph [rankdir=TB, fontname="Helvetica", bgcolor="#e0e0e0", pad=0.25]
    node [shape=plaintext, fontname="Helvetica"]
    stack [label=<
      <table border="0" cellborder="1" cellspacing="0" cellpadding="10" color="#555555">
        <tr><td bgcolor="#ffffff" width="380"><b>Application</b><br/><font point-size="10">HTTP, MQTT, email: unchanged, and never sees the encryption</font></td></tr>
        <tr><td bgcolor="#d0e8d0"><b>TLS</b><br/><font point-size="10">private · unaltered · talking to the right machine</font></td></tr>
        <tr><td bgcolor="#e0f0ff"><b>TCP</b><br/><font point-size="10">delivers bytes reliably and in order, in plain sight</font></td></tr>
        <tr><td bgcolor="#f4f4f4"><b>IP</b><br/><font point-size="10">addresses and routing, hop by hop</font></td></tr>
      </table>
    >]
}
{{< /graphviz >}}

**Every TLS connection answers three questions before it carries any of your data:**

| The question | What answers it | Explained in |
|---|---|---|
| Can anyone else read this? | encryption, with keys that only the two ends have | [encryption](#encryption-keeps-a-conversation-private-but-only-from-people-who-dont-have-the-key) and [key exchange](#public-key-cryptography-lets-strangers-agree-on-a-secret-in-the-open) |
| Did anyone change it on the way? | an integrity check on every message | [hashes](#a-hash-is-a-fingerprint-any-change-to-the-data-changes-it-completely) and [signatures](#a-digital-signature-proves-which-key-signed-something-and-that-nobody-changed-it) |
| Am I talking to who I think I am? | the server's certificate, checked against a CA you already trust | [certificates](#a-certificate-is-a-signed-statement-that-binds-a-name-to-a-public-key), [CAs](#a-certificate-authority-is-a-signer-that-both-sides-already-trust) and [chains](#a-chain-lets-the-root-stay-offline-while-intermediates-do-the-daily-signing) |

**The first two questions are solved problems; the third is why PKI exists.** Strong encryption and
integrity checks are well understood and fast. Proving *who* is on the other end, to a machine that
has never met it, is the hard part, and most of this page is about it. The
[handshake section](#a-tls-connection-opens-with-a-handshake-that-checks-the-server-then-seals-every-message)
puts the pieces back together.

**"SSL" is TLS's old name, and it stuck.** Netscape's **SSL** (Secure Sockets Layer) secured the
early web in the mid-1990s. The IETF standardized its successor as TLS 1.0 in 1999
([RFC 2246](https://www.rfc-editor.org/rfc/rfc2246)). Every SSL version is now retired as insecure
([RFC 7568](https://www.rfc-editor.org/rfc/rfc7568)), and so are TLS 1.0 and 1.1
([RFC 8996](https://www.rfc-editor.org/rfc/rfc8996)). Today's connections use TLS 1.2 or 1.3
([RFC 8446](https://www.rfc-editor.org/rfc/rfc8446)). An "SSL certificate" is the same thing as a
TLS certificate; only the name is old.

## Encryption keeps a conversation private, but only from people who don't have the key

**Symmetric encryption uses one shared secret key to lock and unlock.** Ciphers such as AES are fast
enough to encrypt everything a connection carries, and they are not the weak point. With a good key,
nobody reads the traffic.

**Both sides must hold the same key before they can talk privately.** That is the catch. Two machines
meeting for the first time have no shared secret, and sending one across the network gives it to
everyone listening. This is the **key-distribution problem**, and for most of history it was solved
by couriers and codebooks.

## Public-key cryptography lets strangers agree on a secret in the open

**A key pair is two keys made together: a public key to share and a private key to keep.** What one
does, only the other can check or undo. The public key can be published anywhere. The private key
never leaves its owner, and everything on this page depends on that.

**Key exchange lets two machines make a shared secret that eavesdroppers can't work out.** Each side
makes a short-lived key pair and sends the other its public half. Each combines its own private half
with the other's public half, and both arrive at the same secret, which never crossed the wire. The
method is **Diffie-Hellman** (on today's connections, its elliptic-curve form, ECDHE). That secret
then keys the fast symmetric cipher.

**Key pairs also sign, which is what the rest of PKI is built on.** The common algorithms are RSA,
ECDSA and Ed25519. Their math differs, but they play the same roles here.

## A hash is a fingerprint: any change to the data changes it completely

**A cryptographic hash turns any amount of data into a short fixed-length value.** SHA-256 gives 256
bits, usually written as 64 hex characters. The same input always gives the same hash. Change one
bit of the input and the hash changes beyond recognition, and no one knows how to construct a second
input with the same hash.

**Comparing two hashes compares two files without trusting the path between them.** That is why
software downloads publish a `.sha256`, why a certificate is identified by its **fingerprint** (the
hash of the whole certificate), and why Deevnet's
[CA ceremonies](/docs/runbook/root-of-trust/issuing-ca/) write fingerprints on paper and compare them
on both sides of the offline gap.

## A digital signature proves which key signed something and that nobody changed it

**Signing hashes the data, then transforms the hash with the private key.** Anyone holding the
matching public key can check the result against their own hash of the data. If the check passes,
two things are true: the holder of that private key signed it, and the data hasn't changed by a
single bit since.

**A signature proves which key signed, not which person or machine.** "This was signed by key X" is
all the math gives you. Whether key X belongs to your bank, your router or an attacker is a separate
question, and it is the one PKI exists to answer.

## A public key alone does not say whose it is

**An attacker in the path can hand each side a key of their own.** The client asks for the server's
public key. The attacker intercepts the request and answers with the attacker's own key, then
connects to the real server on the client's behalf. Both connections are encrypted, and the attacker
reads and changes everything that passes. This is the **man-in-the-middle** attack, and encryption
alone does nothing to stop it.

{{< graphviz >}}
digraph mitm {
    graph [rankdir=LR, nodesep=0.4, ranksep=0.9, fontname="Helvetica", bgcolor="#e0e0e0", pad=0.25]
    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=13, margin="0.25,0.12", penwidth=1.2]
    edge [arrowsize=0.7, fontname="Helvetica", fontsize=11, fontcolor="#333333", color="#555555", dir=both]

    client [label=<<b>Your computer</b><br/><font point-size="10">thinks it is talking to the server</font>>, fillcolor="#e0f0ff"]
    attacker [label=<<b>Attacker</b><br/><font point-size="10">decrypts, reads, re-encrypts</font>>, fillcolor="#f6d0d0"]
    server [label=<<b>Real server</b><br/><font point-size="10">thinks it is talking to you</font>>, fillcolor="#d0e8d0"]

    client -> attacker [label="  encrypted with\n  the attacker's key  "]
    attacker -> server [label="  encrypted with\n  the server's key  "]
}
{{< /graphviz >}}

**The client needs a way to tell the server's real key from a substitute.** SSH asks you once, on
first connect ("Are you sure you want to continue connecting?"), and then remembers the key. That
works when you connect to a few machines and can check the fingerprint out of band. It does not
work for the web, where every click may reach a server you have never seen.

## A certificate is a signed statement that binds a name to a public key

**A certificate says "this public key belongs to this name", signed by someone else.** The format is
**X.509**. The server sends its certificate when a connection starts, and the client checks the
signature on it rather than taking the key at face value. The fields a reader meets most often:

| Field | What it says | Example |
|---|---|---|
| Subject | who the certificate is for: CN (common name), O (organization), OU (organizational unit) | `CN=Deevnet Mobile Site CA, OU=Mobile Site, O=Deevnet` |
| Subject Alternative Names (SANs) | every DNS name and IP address the certificate is valid for; clients check the name here, not in the CN | `DNS:example.org`, `IP:10.20.99.40` |
| Issuer | who signed it: the issuer's subject | `CN=Deevnet Root CA, …` |
| Validity | not before / not after | one year for a server, decades for a root |
| Public key | the key being vouched for | RSA 3072, or an elliptic-curve key |
| Key usage | what the key may do: sign data, sign certificates | `keyCertSign` for a CA |
| Extended key usage (EKU) | which role it may play in TLS | `serverAuth`, `clientAuth` |
| Basic constraints | whether it is a CA, and how many CAs may sit below it (`pathlen`) | `CA:TRUE, pathlen:0` |

**A certificate holds no secret.** It is public and handed to anyone who connects. The server proves
it is the certificate's rightful owner by signing part of the connection with the matching private
key, which a copied certificate can't do.

**A certificate signing request (CSR) is how a key holder asks for a certificate.** The requester
makes a key pair, puts the public key and the desired name into a CSR, and signs the CSR with the
private key. The CA checks it and returns a certificate. The private key never travels.

{{< hint info >}}
**Try it: read a website's certificate in your browser.** Click the icon to the left of the address
bar, then follow the connection or security details to the certificate viewer. Look for *Issued
To*, *Issued By*, the validity dates, the subject alternative names and the fingerprints. A second
tab or panel shows the chain, covered below.
{{< /hint >}}

## A certificate authority is a signer that both sides already trust

**A CA's whole job is to check who is asking and then sign the binding.** Before signing, a public
CA verifies that the requester controls the name, for example by asking them to place a token on the
website or in DNS. Then it signs the certificate with its own private key.

**The client checks the CA's signature against a trust store it already has.** A **trust store** is a
list of CA certificates that this computer will believe, installed with the operating system or the
browser before any connection happens. The CAs in it are **trust anchors**.

**Trust is a decision made in advance, not something computed during the connection.** The math can
show that a certificate was signed by a CA in the store. It can't decide whether that CA deserves to
be there. Someone made that decision beforehand: a browser maker, an operating system vendor, an
IT department, or you.

## A chain lets the root stay offline while intermediates do the daily signing

**The trust anchor at the top is a root CA, whose certificate signs itself.** Nothing vouches for a
root except its place in the trust store. That makes a root's private key the most valuable thing in
the system: whoever holds it can make a certificate for any name that every client will believe.

**Roots sign intermediate CAs, and intermediates sign everyday certificates.** A root's key is used
rarely, kept offline, and brought out only to sign a new intermediate. The intermediate's key stays
online and signs the **leaf** certificates that servers and devices use. The client follows the
**chain** upward: leaf, signed by intermediate, signed by root, which is in its store.

{{< graphviz >}}
digraph chain {
    graph [rankdir=TB, nodesep=0.5, ranksep=0.45, fontname="Helvetica", bgcolor="#e0e0e0", pad=0.25]
    node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=13, margin="0.25,0.12", penwidth=1.2]
    edge [arrowsize=0.7, fontname="Helvetica", fontsize=11, fontcolor="#333333", color="#555555"]

    subgraph cluster_offline {
        label=<<b>Offline: </b>used a few times in its life>
        labeljust=l
        fontname="Helvetica"
        fontsize=11
        style="dashed,rounded,filled"
        fillcolor="#f5ead8"
        color="#a0855b"
        margin=14
        root [label=<<b>Root CA</b><br/><font point-size="10">self-signed · in the trust store · decades</font>>, fillcolor="#f6e3c4"]
    }

    subgraph cluster_online {
        label=<<b>Online</b>>
        labeljust=r
        labelloc=b
        fontname="Helvetica"
        fontsize=11
        style="dashed,rounded,filled"
        fillcolor="#eef3f8"
        color="#6b8aa8"
        margin=14
        inter [label=<<b>Intermediate CA</b><br/><font point-size="10">signs every day · years</font>>, fillcolor="#e0f0ff"]
    }

    leaf [label=<<b>Leaf: www.example.org</b><br/><font point-size="10">sent by the server · months</font>>, shape=note, style=filled, fillcolor=white]

    root -> inter [label="  signs"]
    inter -> leaf [label="  signs"]
}
{{< /graphviz >}}

**Losing an intermediate is a repair; losing a root is a rebuild.** A stolen intermediate key is
revoked and replaced, and clients go on trusting the root. A stolen root key means every trust store
holding that root must remove it and install a new one, on every machine. Keeping the root offline is
what makes the first case the likely one.

**`pathlen` limits how deep a chain may grow below a CA.** An intermediate with `pathlen:0` may sign
leaves but no further CAs, so even a stolen intermediate can't create CAs of its own.

## A TLS connection opens with a handshake that checks the server, then seals every message

**A TLS connection runs in two phases: a handshake, then sealed records.** The handshake is a short
scripted exchange that agrees on keys and proves the server's identity. It costs one round trip in
TLS 1.3, a few milliseconds on a local network. Everything after it is the application's data,
sealed with the keys the handshake agreed.

{{< mermaid >}}
sequenceDiagram
    participant C as Client (your browser)
    participant S as Server (example.org)
    C->>S: ClientHello: TLS versions, ciphers, a key share, the name it wants
    S->>C: ServerHello: the chosen cipher and its own key share
    Note over C,S: Both now compute the same session keys. Everything below is encrypted.
    S->>C: Certificate: the leaf and its intermediates
    S->>C: CertificateVerify: a signature over the handshake so far
    S->>C: Finished
    Note over C,S: The client checks the chain, the dates, the name and the key usage
    C->>S: Finished
    C->>S: Application data, such as the HTTP request
    S->>C: Application data, such as the web page
{{< /mermaid >}}

**The handshake in order** (TLS 1.3):

1. **The client says hello and names the server it wants.** Its *ClientHello* lists the TLS versions
   and **cipher suites** (the encryption and integrity algorithms) it supports, carries its half of
   a key exchange, and names the host it is trying to reach (**SNI**, server name indication), so a
   server hosting many sites knows which certificate to send.
2. **The server picks, and both sides compute the same session keys.** The *ServerHello* picks a
   version and a cipher suite and carries the server's half of the key exchange (ECDHE). From here
   on, the rest of the handshake is encrypted.
3. **The server sends its certificate and the intermediates.** The root is not sent; the client
   must already have it.
4. **The server signs the handshake so far with its private key.** This proves it holds the key in
   the certificate, which a copied certificate can't fake. It also ties the identity to *this*
   connection's key exchange, so an attacker in the middle can't splice in a different one.
5. **The client checks the certificate.** It builds a chain from the leaf to a root in its trust
   store and checks each signature on the way up. It checks that today falls within each
   certificate's validity dates, that the name it dialed is in the leaf's SANs, and that the EKU
   allows `serverAuth`. **If anything fails, the client stops and warns**, and no application data
   is sent.
6. **Both sides send *Finished*,** a check over the whole handshake that catches any message an
   attacker altered along the way.

**After the handshake, every message travels as a sealed record.** The application's data is cut
into records, and each is encrypted and given an integrity tag with the session keys. A record
altered in transit fails its check, and the connection is closed. This part is fast symmetric
cryptography; the slow public-key work happened once, in the handshake.

**Session keys are new for every connection.** Because each side's key-exchange half is thrown away
afterward, someone who records today's traffic and steals the server's private
key next year still can't decrypt it. This is **forward secrecy**, and TLS 1.3 builds it into every full handshake. The
server's long-lived key only *signs*; it never encrypts the session.

{{< hint info >}}
**Try it: watch a server send its chain.** From any machine with OpenSSL:

```bash
openssl s_client -connect example.org:443 -servername example.org -showcerts </dev/null
```

`-servername` sets the SNI from step 1. Each certificate prints as `s:` (subject) and `i:`
(issuer). Each issuer is the next one's subject,
up to a certificate whose issuer is a root in your store. The `Verify return code: 0 (ok)` line near
the end means the chain checked out.

To read the leaf's fields:

```bash
openssl s_client -connect example.org:443 -servername example.org </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName,extendedKeyUsage,basicConstraints
```

Expect `CA:FALSE`, the site's names under the subject alternative name, and `TLS Web Server
Authentication` as the extended key usage.
{{< /hint >}}

## On the internet this is invisible because the trust decisions were made for you

**Your trust store came with your device.** Each major platform runs a **root program** that decides
which CAs its users trust: Mozilla (Firefox, and most Linux distributions, which ship Mozilla's
list), Apple, Microsoft, and Google's
[Chrome Root Program](https://chromium.googlesource.com/website.git/+/HEAD/site/Home/chromium-security/root-ca-policy/index.md).
A CA gets in by passing audits and stays in by following the programs' rules. Updates arrive with
ordinary software updates.

**Public CAs all follow one rulebook.** The **CA/Browser Forum**, where CAs and browser makers sit
together, publishes the
[Baseline Requirements](https://cabforum.org/working-groups/server/baseline-requirements/requirements/):
how a CA must check a requester, what a certificate may contain, and how long it may last. The root
programs require them.

**Every public certificate is logged where anyone can see it.** **Certificate Transparency** (CT,
[RFC 6962](https://www.rfc-editor.org/rfc/rfc6962)) records each certificate in public, append-only
logs. Chrome has refused publicly trusted server certificates issued after April 30, 2018 that are
not logged
([Chromium](https://chromium.googlesource.com/chromium/src/+/lkgr/net/docs/certificate-transparency.md)).
A certificate wrongly issued for your name can't be issued quietly, and site owners can watch the
logs for their names.

**Issuance and renewal became automatic and free.** The **ACME** protocol
([RFC 8555](https://www.rfc-editor.org/rfc/rfc8555)), built for Let's Encrypt, lets a server prove
it controls its name and fetch a certificate with no person involved, then renew it on a schedule.
Lifetimes are shrinking on purpose because renewal is now automatic: public certificates may last
at most 200 days from March 2026, 100 from 2027 and 47 from 2029 (Baseline Requirements §6.3.2).

**So a person sees a padlock, or a warning, and nothing else.** All the trust decisions were made by
the root programs, and all the certificate work is done by machines. The PKI only becomes visible
when something fails.

## Trust breaks in three ways: a certificate expires, is revoked, or its CA is distrusted

**An expired certificate fails everywhere at once.** Validity dates are absolute, so a certificate
nobody renewed takes its service down at the same moment for every client. A client with a wrong
clock can fail the same way on a certificate that is fine.

**Revocation cancels a certificate before it expires, and it has never worked well.** A CA lists
revoked certificates in a **CRL** (certificate revocation list) or answers queries about them over
**OCSP**. Clients often skip the check when they can't reach the CA, and OCSP tells the CA which site
each user is visiting. Let's Encrypt
[turned its OCSP service off](https://letsencrypt.org/2025/08/06/ocsp-service-has-reached-end-of-life)
in August 2025, citing that privacy cost, and publishes CRLs instead. Short lifetimes are the other
answer: a certificate that expires in weeks needs revoking less.

**A CA that breaks the rules is removed from the trust stores, and every certificate under it stops
working.** In 2011 attackers broke into DigiNotar, a Dutch CA, and issued fraudulent certificates,
including one for `*.google.com` that was used to intercept users' connections. Mozilla
[removed DigiNotar from its trust store entirely](https://blog.mozilla.org/security/2011/09/02/diginotar-removal-follow-up/),
as the other root programs did. A CA's trustworthiness, not its math, is what the system rests on.

## Mutual TLS makes the server check the client too

**In ordinary TLS only the server has a certificate.** The client stays anonymous at the TLS layer
and proves who it is afterward, with a password or a token.

**With mutual TLS (mTLS), the client presents a certificate as well.** The server asks for one in the
handshake, then checks it the same way a client checks a server's: chain, dates, signature, and an
EKU that allows `clientAuth`. The client proves it holds the private key by signing the handshake.

**mTLS suits devices because the identity is the key, and the key never leaves the device.** There
is no password to type, reuse or leak, and the server can read which device is connecting from the
certificate itself. It needs a CA willing to issue client certificates, and public CAs are leaving
that business: Let's Encrypt
[removed client authentication](https://letsencrypt.org/2025/05/14/ending-tls-client-authentication)
from its certificates in 2026.

## A private network needs its own CA, because a public CA cannot vouch for private names

**Public CAs may only certify names that the public internet can check.** Since 2015, publicly
trusted certificates may not carry an internal name or a private IP address
([CA/Browser Forum](https://cabforum.org/working-groups/server/internal-names/)). A lab's
`10.x.x.x` addresses and its internal names are outside what any public CA may sign.

**Running your own CA means making the trust decision yourself.** Nothing trusts a private root by
default. You install it in the trust store of each machine, browser and device that should believe
it, which is the job a root program does for the public web. In exchange, you choose the names, the
fields, the lifetimes and who may get a certificate, and nothing about your network appears in a
public log.

**The same ideas carry over to Deevnet under Deevnet's own names:**

| Primer idea | Deevnet's version |
|---|---|
| Offline root, in every trust store | the **Deevnet Root CA**, held offline by the operator ([Trust and Identity](/docs/architecture/trust-and-identity/)) |
| Intermediate CAs | a **Site CA** per site, also offline, and under it two issuing CAs per site |
| Leaf certificates for servers (`serverAuth`) | issued by the site's **Substrate CA**, through site automation |
| Client certificates for mTLS (`clientAuth`) | issued by the site's **Tenant Device CA**, to tenant devices |
| The rulebook | the [Certificates standard](/docs/standards/certificates/) and [ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/) |
| Signing with an offline key, hashes compared on paper | the [Root of Trust](/docs/runbook/root-of-trust/) ceremonies |
| Installing the root where it is trusted | [where the Deevnet Root CA is trusted](/docs/architecture/trust-and-identity/#where-the-deevnet-root-ca-is-trusted) |

Trust and Identity also sets out in full
[why Deevnet uses a private PKI rather than a public CA](/docs/architecture/trust-and-identity/#a-private-pki-because-a-public-ca-cannot-certify-what-a-site-serves).

## Terms at a glance

| Term | Meaning |
|---|---|
| TLS | Transport Layer Security: the protocol that makes a connection private, unaltered and authenticated |
| SSL | TLS's predecessor and old name; every version is retired, but "SSL certificate" lives on |
| HTTPS | HTTP carried inside TLS; the padlock in a browser |
| Handshake | the opening exchange of a TLS connection: agree on keys, prove the server's identity |
| Cipher suite | the set of algorithms a connection uses for encryption and integrity |
| SNI | server name indication: the host name the client asks for in its first message |
| Session keys | symmetric keys made fresh for one connection by the key exchange, then thrown away |
| Forward secrecy | a stolen long-term key can't decrypt connections recorded earlier |
| Key pair | a public key to share and a private key to keep, made together |
| Hash, fingerprint | a short fixed-length value that changes completely if the data changes; a certificate's fingerprint is its hash |
| Digital signature | proof that a given private key signed exactly this data |
| Certificate (X.509) | a signed statement binding a name to a public key |
| CSR | certificate signing request: a public key and a name, signed by the matching private key |
| CA | certificate authority: signs certificates for others |
| Root CA | a self-signed CA trusted directly from a trust store |
| Intermediate (issuing) CA | a CA signed by another CA, which signs leaves or further CAs |
| Leaf | an end certificate for a server or a device, which signs no certificates |
| Chain | the path of signatures from a leaf up to a root |
| Trust store, trust anchor | the CA certificates a machine believes, and each one in it |
| SAN | subject alternative name: the DNS names and IP addresses a certificate is valid for |
| EKU | extended key usage: `serverAuth`, `clientAuth` and other roles a certificate may play |
| `pathlen` | how many CAs may sit below a CA in a chain |
| PEM | the text encoding of certificates and keys, between `-----BEGIN …-----` lines |
| mTLS | mutual TLS: both sides present certificates |
| CT | Certificate Transparency: the public logs of every publicly trusted certificate |
| ACME | the protocol that automates issuing and renewing certificates |
