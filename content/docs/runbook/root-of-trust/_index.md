---
title: "Root of Trust"
weight: 1
bookCollapseSection: true
---

# Root of Trust

Every certificate Deevnet issues chains to one root, the **Deevnet Root CA**, and each site has its
own **Site CA** under it ([Trust and Identity](/docs/architecture/trust-and-identity/),
[ADR-0031](/docs/architecture/decisions/substrate/0031-deevnet-pki/)). The Deevnet Root CA and Site
CA private keys are generated and maintained offline and are never available to site automation or
networked systems.

These pages are the key holder's procedures. They run on an offline machine, rarely:

| Ceremony | When | Page |
|---|---|---|
| Prepare the offline machine | before every ceremony | [Preparing](/docs/runbook/root-of-trust/preparing/) |
| Generate the Deevnet Root CA | once, for the whole organization | [Root CA](/docs/runbook/root-of-trust/root-ca/) |
| Create a Site CA | once per site (mobile, home, …), and every ten years | [Site CA](/docs/runbook/root-of-trust/site-ca/) |
| Sign an issuing CA | when a site's Substrate CA or Tenant Device CA is created or rotated, about every five years | [Issuing CA](/docs/runbook/root-of-trust/issuing-ca/) |
| Check, back up, recover | yearly, and after a loss | [Custody](/docs/runbook/root-of-trust/custody/) |

## Only certificates and signing requests cross to automation

Only public material leaves the offline machine:

- **certificates:** the root's, each Site CA's, and each signed issuing CA's;
- **certificate signing requests**, which come *in* from automation to be signed.

They cross on the **transfer media**, the only thing that moves between the online and offline
machines. The Root CA's and Site CAs' keys stay on their own **key media**, which is only ever
plugged into the offline machine. A key never leaves the offline machine except as an encrypted file
onto that key media.

An issuing CA's key is generated where it will live (site automation for the Substrate CA, the secret
store for the Tenant Device CA), and only its request is brought to the ceremony. Two small tools in
`ansible-collection-deevnet.mgmt/scripts/pki/` move it and its certificate across, with a manifest of
hashes each way, a refusal of any private key on the transfer media, and checks of the request, the
signature and the chain ([Issuing CA](/docs/runbook/root-of-trust/issuing-ca/)). They automate the
mechanics and the checking. Signing stays a decision the key holder makes by typing the CA's name.

## Every certificate names its organization, its unit and itself

Every subject carries an organization, an organizational unit and a common name, so a certificate's
*Issued To* and *Issued By* read plainly ([Certificates standard](/docs/standards/certificates/)):

| Certificate | O | OU | CN |
|---|---|---|---|
| Root | Deevnet | Deevnet PKI | Deevnet Root CA |
| Site CA | Deevnet | Mobile Site | Deevnet Mobile Site CA |
| Substrate CA | Deevnet | Mobile Site | Deevnet Mobile Substrate CA |
| Tenant Device CA | Deevnet | Mobile Site | Deevnet Mobile Tenant Device CA |
