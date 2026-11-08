---
title: "deevnet-kit"
weight: 5
---

# deevnet-kit

The Deevnet API's stand-in on a Raspberry Pi. On the take-home Pi backend image it does, for one
tenant and on the Pi itself, what the API does for a tenant on the site: broker accounts, log users,
the server certificate, and a Grafana organization. It is built from the API's own packages, so the
same rules apply in both places.

| | |
|---|---|
| **Source** | `deevnet-provisioning-api`, `cmd/deevnet-kit`; it shares the API's tag |
| **Built by** | `make build-pi` and `make stage-pi` in the API repository (linux/arm64), baked into the image by `make pi-backend` in `deevnet-image-factory` |
| **Runs as** | A CLI and three systemd units on the Pi: first boot, dashboards, and a self-test on every boot |
| **Commands** | `init`, `status`, `env`, `export`, `account add\|list\|rm`, `names`, `regen-certs`, `cert request`, `cert install`, `render`, `dashboards`, `selftest` |
| **State** | `/etc/deevnet-kit/` (the tenant and its tokens, accounts, TLS, Grafana settings, and which PKI the card is on); input from `/boot/firmware/deevnet-kit.txt` |

---

## The card's certificate

**Every card starts on a CA of its own**, made at first boot, which signs its server certificate for
its hostname, `localhost`, and any extra names and addresses set with `names` (`regen-certs` reissues
it). Nothing outside the card trusts that CA until someone installs it.

**A card becomes a Deevnet Pi when a certificate from the Tenant Service CA is installed**
([ADR-0041](/docs/architecture/decisions/tenant-model/0041-take-home-pi-pki-lifecycle/) §2,
[CHG-0056](/docs/changes/2026/0056-kit-deevnet-or-own-pki/)). `cert request` makes a new key on the
Pi and a signing request; the request is signed in a work session at the Mobile Factory, through the
tenant's `deevnet_certificate`; `cert install FULLCHAIN ROOT` installs what comes back. Before it
touches anything, it checks that the certificate is for the pending key, chains to the root given,
and names `mqtt`, `logs` and `grafana` under `<tenant>.deevnet.net`. Then:

- the certificate becomes the server's, and the Deevnet Root becomes `ca.pem`, what every service on
  the Pi trusts; the card's own CA is kept as `card-ca.pem`;
- the Pi's own services dial its site-less names, mapped to loopback in a block of `/etc/hosts`, so
  the certificate needs neither `localhost` nor an address;
- `kit.env` and `export` hand an app those names and `deevnet-root-ca.pem`;
- Grafana's log data sources are written again for `logs.<tenant>.deevnet.net`.

**The key never leaves the Pi, and no CA key is on it.** `regen-certs` refuses on a Deevnet Pi,
where it would sign with the card's CA. The certificate is renewed by installing what
`deevnet_certificate` issues for the same key once sixty days remain: `cert install` takes a
certificate for the key the Pi already serves, if it chains to the root the Pi already trusts and
names the same services, and replaces only the certificate. Requesting and installing again renews
it with a new key. `status` and `selftest` warn on a Deevnet Pi when the certificate is missing one
of those names, never about addresses, which it does not hold. `deevnet-kit` v0.15.0 renews only
with a new key, leaves the data sources on `localhost`, and warns about every address.

**`deevnet-kit pki` moves a Pi to a PKI of its owner's own** (ADR-0041 §3, §4). It runs the
ceremony tools the image carries (`deevnet-pki-owner.sh`, from `deevnet.mgmt`): `pki init` makes the
owner's root on an encrypted USB stick and an issuing CA on the Pi, and changes nothing served;
`export` then hands out `trust-bundle.pem`, the root trusted now and the owner's. `pki switch`
reissues the Pi's certificate from the owner's CA and makes the owner's root what every service
trusts, keeping the one before as `previous-root.pem`. Before using anything the tool made, the kit
checks the issuing CA chains to the root, may sign only leaves, is constrained to the owner's
names, and that no root key is on the Pi. The issuing CA may name `.local`, `localhost`, private
and loopback addresses and the owner's domains; on a Deevnet Pi, also `<tenant>.deevnet.net`, so
the certificate keeps the kit's names and a device verifying one keeps working. `pki enroll` issues
a device's certificate, `pki issuing` a new card's issuing CA from the stick, and `regen-certs`
renews from the owner's CA. There is no first-boot switch between Deevnet and an owner's own PKI:
running `pki init` is the choice.

It is not part of the deployed API. How a tenant uses the image is
[Tenant to Pi Image](/docs/runbook/tenant/tenant-to-pi-image/).
