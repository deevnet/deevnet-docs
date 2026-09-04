---
title: "Credential Rotation"
weight: 6
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 9
---

# Credential Rotation

Define how a credential gets replaced. The [Secure Identity Standard](/docs/standards/secure-identity/) already says credentials should be short-lived; nothing says how to make one short-lived, or what to do when a specific one is exposed.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

The standard's §1.1 is unambiguous about intent:

> Clients MAY hold long-lived **identity** material (e.g., SSH private keys). Everything else should trend short-lived … If compromise of a single laptop exposes long-lived secrets, the design is incorrect.

But the word *rotation* does not appear anywhere in it. The substrate today runs on static, long-lived credentials — API tokens, vault passphrases, TSIG keys, the automation SSH key — with no defined lifetime, no inventory of where each is used, and no procedure for replacing one. The standard describes the destination; there is no route.

This is **not** an urgent security posture item. dvntm is a lab on hardware that is treated as ephemeral, the blast radius is a home network, and nothing here is internet-facing. It is on the roadmap because the *process* is missing, and because the first time a credential genuinely needs replacing is the worst time to design the procedure.

**In Scope**

- An inventory of every long-lived credential, what it authenticates, and what consumes it
- A written rotation procedure per credential class, including the consumers that must be updated in the same operation
- Wherever practical, shortening lifetimes so rotation is routine rather than exceptional

**Out of Scope**

- Tenant-held credentials. Under [ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/) a tenant's per-tenant MinIO credential is the tenant's own; the substrate issues it and does not manage its lifecycle.
- Building a secrets manager. §4.3 says IaC must reference secret *locations* rather than values; choosing and deploying the thing those locations point at is a separate, larger project.

---

## Credential Inventory ⏳

- ⏳ Enumerate every long-lived credential in the substrate and record, for each, what it authenticates, which repos and roles consume it, and whether a copy exists outside the vault
- ⏳ Identify which are **derivable or reissuable without coordination** (a Proxmox API token) versus which require simultaneous updates on both sides (a TSIG key shared with a tenant's Terraform)

Known members of that set today, none with a defined lifetime:

- Proxmox API tokens per hypervisor (`vault_proxmox_token_id` / `_secret`), rendered to `build/pve-env/*.env` on disk by the image factory
- The OPNsense API key/secret pair for the core router
- The `a_autoprov` SSH keypair — long-lived by design under §1.1, but with no defined replacement procedure
- The ansible-vault passphrase itself, which has no password file and is only in the operator's head
- Per-tenant TSIG keys and per-tenant MinIO credentials, both shared with tenant repos

## Rotation Procedures ⏳

- ⏳ Write a procedure per credential class, each naming every consumer that must change in the same operation. A rotation that updates the issuer and misses a consumer is an outage, and for anything the substrate does not prune, it is a silent one
- ⏳ Decide whether rotation is scheduled, event-driven (exposure, operator change, hardware disposal), or both
- ⏳ Cover the awkward case explicitly: a credential shared with a tenant repo cannot be rotated unilaterally, so the procedure needs a handshake or a dual-key overlap window

## Reducing Lifetime ⏳

- ⏳ Assess which static credentials can become short-lived without a secrets manager — Proxmox API tokens support expiry dates, which would make rotation forced rather than optional
- ⏳ Record which ones genuinely cannot yet, and why, so the gap is a documented decision rather than an oversight

## Handling Exposure ⏳

- ⏳ Write down what "exposed" means here and what follows from it. A credential printed to a terminal, a log, a chat transcript or a CI job output is exposed even if the audience was trusted; the question is what the response is, not whether it felt risky at the time
- ⏳ Establish the default: in a lab with an ephemeral substrate, "reissue at the next convenient rebuild" is a legitimate answer — but it should be a stated policy rather than an implicit one
