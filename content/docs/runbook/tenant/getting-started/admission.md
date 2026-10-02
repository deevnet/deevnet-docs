---
title: "Admission"
weight: 2
---

# Admission

A tenant starts with a **name**, and the operator admitting it. That is the only thing the operator
does for you; everything after it you do yourself.

## Pick a name

- 1 to 8 characters, lowercase letters and digits, **starting with a letter** — `^[a-z][a-z0-9]{0,7}$`.
  The limit is the tenant hypervisor's: your network's SDN zone ID is your name verbatim, and
  Proxmox caps zone IDs at 8 characters
- It becomes your DNS zone (`<name>.mobile.deevnet.net`), your MQTT topic prefix (`<name>/…`) and
  the name of your network. Pick something you will not mind seeing everywhere
- `sensors`, `bench1`, `ptv` are fine; `Pico-Demo` and `greenhouse1` are not

## Ask the operator

Tell the operator the name. They run one API call
([Tenant Admission](/docs/runbook/substrate/tenant-admission/)) and hand you four things:

1. an **enrollment token** (it looks like `s.…`)
2. the **API endpoint**, `https://api.mobile.deevnet.net:8080`
3. the **`DVNTM-TD` Wi-Fi key**, for the network you work from
4. the **site CA**, `deevnet-mobile-root-ca.pem`

## What the token is

| | |
|---|---|
| Single use | your first `terraform apply` spends it, and hands you your own long-lived token in exchange |
| Bound to your name | presenting it for any other name **spends it** and fails with `401` — a typo costs a new admission |
| Expires | after **72 hours**. Admit close to when you will apply |

Treat it like a password until it is spent. Once it is spent it is worthless, and from then on your
credential is the tenant token in your Terraform state.

If the operator gets `409`, the name is already taken — by someone else, or by you last time. A
tenant that already exists does not need admitting again; it needs its own token.
