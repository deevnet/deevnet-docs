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
- `kit.env` and `export` hand an app those names and `deevnet-root-ca.pem`.

**The key never leaves the Pi, and no CA key is on it.** `regen-certs` refuses on a Deevnet Pi,
where it would sign with the card's CA; the certificate is renewed by requesting and installing
again. The first-boot switch between Deevnet and an owner's own PKI, and `pki init` for the latter,
are not built yet (CHG-0056).

It is not part of the deployed API. How a tenant uses the image is
[Tenant to Pi Image](/docs/runbook/tenant/tenant-to-pi-image/).
