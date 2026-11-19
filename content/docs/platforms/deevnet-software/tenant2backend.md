---
title: "tenant2backend"
weight: 5
aliases: ["/docs/platforms/deevnet-software/deevnet-kit/"]
---

# tenant2backend

The Deevnet API's stand-in on a take-home backend. On every take-home image, the Pi's, the virtual
machine's and the installer's, it does for one tenant, on the backend itself, what the API does for
a tenant on the site: broker accounts, log users, the server certificate, a Grafana organization,
alert rules and buckets. It is built from the API's own packages, so the same rules apply in both
places.

**It was `deevnet-kit` until v0.28.0** ([ADR-0045](/docs/architecture/decisions/tenant-model/0045-take-home-tool-owners-name/)):
the backend is its owner's, so its tool and files carry no brand. Its files are under `/etc/backend`,
its units are `backend-*`, its group is `backend`, and its CA is exported as `backend-ca.pem`. A
backend flashed from an earlier image keeps the old names; on the first images with the new ones,
`deevnet-kit` is still a link to it, for one release.

| | |
|---|---|
| **Source** | `deevnet-provisioning-api`, `cmd/tenant2backend`; it shares the API's tag |
| **Built by** | `make stage-pi` (linux/arm64) and `make stage-vm` (linux/amd64) in the API repository, baked into each image by `deevnet-image-factory` |
| **Runs as** | A CLI and its `backend-*` systemd units: first boot, the console setup on a virtual machine, dashboards, alerting, and a self-test on every boot |
| **Commands** | `setup`, `init`, `status`, `env`, `export`, `account add\|list\|rm`, `names`, `regen-certs`, `cert request`, `cert install`, `pki`, `render`, `dashboards`, `alerts`, `notify`, `bucket`, `selftest` |
| **State** | `/etc/backend/` (the tenant and its tokens, accounts, TLS, Grafana settings, buckets, and which PKI the backend is on); input from `/boot/firmware/backend.txt` on a Pi, or from `setup` on the console |

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

**`tenant2backend pki` moves a Pi to a PKI of its owner's own** (ADR-0041 §3, §4). It runs the
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
[Take Your Tenant Home](/docs/runbook/tenant/take-it-home/).
