---
title: "Credential Rotation: Project Plan"
linkTitle: "Project Plan"
aliases:
  - /docs/projects/credential-rotation/
  - /projects/credential-rotation/
weight: 8
tasks_completed: 5
tasks_in_progress: 0
tasks_planned: 7
---

# Credential Rotation: Project Plan

Define how a credential gets replaced. The [Secure Identity Standard](/docs/standards/secure-identity/) already says credentials should be short-lived; nothing says how to make one short-lived, or what to do when a specific one is exposed.

**Roadmap item:** [Credential Rotation](/docs/roadmap/infrastructure/substrate/credential-rotation/)

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

The standard's §1.1 is unambiguous about intent:

> Clients MAY hold long-lived **identity** material (e.g., SSH private keys). Everything else should trend short-lived … If compromise of a single laptop exposes long-lived secrets, the design is incorrect.

But the word *rotation* does not appear anywhere in it. The substrate today runs on static, long-lived credentials — API tokens, vault passphrases, TSIG keys, the automation SSH key — with no defined lifetime, no inventory of where each is used, and no procedure for replacing one. The standard describes the destination; there is no route.

This is **not** an urgent security posture item. mobile is a lab on hardware that is treated as ephemeral, the blast radius is a home network, and nothing here is internet-facing. It is on the roadmap because the *process* is missing, and because the first time a credential genuinely needs replacing is the worst time to design the procedure.

**In Scope**

- An inventory of every long-lived credential, what it authenticates, and what consumes it
- A written rotation procedure per credential class, including the consumers that must be updated in the same operation
- Wherever practical, shortening lifetimes so rotation is routine rather than exceptional

**Out of Scope**

- Tenant-held credentials. Under [ADR-0007](/docs/architecture/decisions/tenant-model/0007-terraform-state-custody/) a tenant's per-tenant MinIO credential is the tenant's own; the substrate issues it and does not manage its lifecycle.
- Building a secrets manager. §4.3 says IaC must reference secret *locations* rather than values; choosing and deploying the thing those locations point at is a separate, larger project.

---

## Credential Inventory 🔄

- ✅ Enumerate every long-lived credential in the substrate and record, for each, what it authenticates, which repos and roles consume it, and whether a copy exists outside the vault
- ✅ Identify which are **derivable or reissuable without coordination** (a Proxmox API token) versus which require simultaneous updates on both sides (a TSIG key shared with a tenant's Terraform)

**The credentials, ordered by what losing control of each would reach.** None has a defined
lifetime. **Used by** names what reads each one, by repository and role (collections are
`deevnet.mgmt`, `deevnet.net` and `deevnet.builder`; every vault variable is mapped in
`ansible-inventory-deevnet`). **Reissue** says whether it can be replaced **alone**, with every
consumer deployed from the inventory in one change, or needs **both sides**, because a consumer
outside the substrate's automation must change at the same time. The last column says whether
replacing it is written down today. Read from the inventory and the collections on 2026-11-03.

| Credential | Reaches | Used by | Reissue | Rotation written |
|---|---|---|---|---|
| The ansible-vault password | every secret in the vault, including OpenBao's unseal share 1 | Every Ansible run against the inventory, and the image factory's builds. The operator types it or sets `ANSIBLE_VAULT_PASSWORD_FILE`, so a copy lives wherever that file does | Alone (`ansible-vault rekey`), but every copy of the file changes | No |
| The `a_autoprov` SSH key | root on every substrate host | Every collection's `ansible.cfg` (`remote_user`); the image factory bakes the public key into images, and the artifact server publishes it | Alone, with an overlap: every host accepts the new key before the old one goes | No |
| OpenBao's unseal shares (any two of three) | every secret OpenBao holds | `make bao-open`, in a work session | Alone: `make bao-rotate-shares` | Yes ([OpenBao's Keys](/docs/runbook/substrate/building-recovery/openbao-keys/#rotating-the-shares)) |
| The backup age identity | every backup | `deevnet.mgmt` `backup` role and playbook | Alone for new backups; old backups stay readable only with the old identity | No |
| The Deevnet API operator token | every API route, every tenant | `deevnet.mgmt` `deevnet_api` role; read from the running container by `scripts/lib/deevnet-api.sh` (tenant admission) | Alone | No |
| The API's tenant-token signing key | could forge any tenant's token | `deevnet.mgmt` `deevnet_api` role | Both sides: every tenant token stops working and each tenant needs a new one | No |
| The Substrate CA key | any substrate server certificate | `deevnet.builder` `substrate_cert` role and `substrate-ca.yml` | Both sides: every server certificate is reissued and every client's trust updated | Yes ([Custody](/docs/runbook/root-of-trust/custody/)) |
| The tenant service and device CA keys | any tenant service or device certificate | `deevnet.mgmt` `openbao` role, and the `tenant-cas.yml`, `tenant-service-ca.yml` and `tenant-device-ca.yml` playbooks | Both sides: tenants' devices and services trust the CA | Yes ([Rotating](/docs/runbook/substrate/certificates/rotating/)) |
| OpenBao AppRole credentials (Ansible's and the image factory's) | what each role's OpenBao policy grants | `deevnet.mgmt` `openbao` and `deevnet_api` roles; the image factory | Alone | No |
| OPNsense API key, shared by Ansible and the Deevnet API | the whole core router | `deevnet.net` `opnsense_*` roles and service playbooks; the Deevnet API (`deevnet_api` group vars) | Alone | No |
| Proxmox API tokens (build and the API's) | each hypervisor | Build token: `deevnet.builder` `proxmox_vm`, `proxmox_node_network` and `vm_identity` roles, the image factory's Packer templates, and the tenant fabric's Terraform. The API's: `deevnet_api` | Alone | Yes ([Build-Time Secrets](/docs/runbook/substrate/building-recovery/build-secrets/)) |
| Omada Owner, automation user and Open API clients | the controller, the switch's and AP's configuration | `deevnet.net` `omada-automation-user.yml` and `omada-wireless.yml`; the Deevnet API (its own Open API client) | Alone | Automation user only (re-run its play) |
| PowerDNS API key, MinIO root and the API's MinIO admin | every tenant zone; every bucket | `deevnet.mgmt` `powerdns` and `minio` roles; the Deevnet API | Alone | No |
| VerneMQ cookie and database passwords; the broker-writer and log-writer keys | the broker's accounts; the log store's routes | `deevnet.mgmt` `vernemq` and `log_bridge` roles; the Deevnet API | Alone | Broker-writer key only |
| Grafana admin and secret key; the log bridge's token; the vmauth operator token | every tenant's dashboards and log partitions | `deevnet.mgmt` `grafana`, `victorialogs` and `log_bridge` roles; the Deevnet API | Alone | No |
| The API's database password and the egress agent's token | the API's records; the fabric's egress list (`GET /v1/fabric/egress`) | `deevnet.mgmt` `deevnet_api` role; `deevnet.net` `tenant_egress_agent` role | Alone | No |
| The switch and AP admin logins; the shared Wi-Fi keys | each device; each SSID | The switch login: `deevnet.net`, over SSH (`switches` group). The AP's standalone login: `omada-wireless.yml`. Wi-Fi keys: every device that joins | Logins alone; Wi-Fi keys both sides, since every device rejoins | No |
| Per-tenant credentials the API issues (API token, TSIG key, state keys, log tokens, dashboard password, Wi-Fi keys, broker accounts) | that tenant | Issued by the Deevnet API; held in the tenant's own repository, Terraform state and devices | Both sides: a handshake with the tenant | Wi-Fi keys and broker accounts only |

**Rotation is written as each change touches a credential.** A change that adds, narrows or replaces
a credential documents how to rotate it, rather than this project writing every procedure at once
([2026-10 review, A8](/docs/architecture/reviews/2026-10-rebuild-and-access/#a8-rotation)). The three
at the top need their own:

- ⏳ Rekey the ansible-vault password (`ansible-vault rekey`), and what has to be updated with it
- ⏳ Replace the `a_autoprov` SSH key on every host, from the artifact server's published copy onward
- ✅ Rotate OpenBao's unseal shares: `make bao-rotate-shares`, run on 2026-11-08 (CHG-0053)

## Rotation Procedures ⏳

- ⏳ Write a procedure per credential class, each naming every consumer that must change in the same operation. A rotation that updates the issuer and misses a consumer is an outage, and for anything the substrate does not prune, it is a silent one
- ⏳ Decide whether rotation is scheduled, event-driven (exposure, operator change, hardware disposal), or both
- ⏳ Cover the awkward case explicitly: a credential shared with a tenant repo cannot be rotated unilaterally, so the procedure needs a handshake or a dual-key overlap window

## Reducing Lifetime ⏳

- ⏳ Assess which static credentials can become short-lived without a secrets manager — Proxmox API tokens support expiry dates, which would make rotation forced rather than optional
- ⏳ Record which ones genuinely cannot yet, and why, so the gap is a documented decision rather than an oversight

## Handling Exposure ✅

- ✅ Write down what "exposed" means here and what follows from it. A credential printed to a terminal, a log, a chat transcript or a CI job output is exposed even if the audience was trusted; the question is what the response is, not whether it felt risky at the time
- ✅ Establish the default: in a lab with an ephemeral substrate, "reissue at the next convenient rebuild" is a legitimate answer — but it should be a stated policy rather than an implicit one

Both are in the [Exposed Credentials](/docs/policies/risk-management/exposed-credentials/) policy.
