---
title: "ADR-0028: Tenant Workload Login"
weight: -28
---

# ADR-0028: A Tenant Logs In to Its Own Workloads With Its Own Key

|  |  |
|--|--|
| **Status** | Proposed |
| **Date** | 2026-09-27 |
| **Scope** | How a tenant gets a shell on a workload it owns: which account, which key, which template, and from where. Not how code arrives unattended (ADR-0017), and not people's identities (ADR-0025). |
| **Answers** | [ADR-0018: Operator Access to Tenants](/docs/architecture/decisions/tenant-networking/0018-operator-access-to-tenants/), open question 3 |
| **Related** | [ADR-0015: Tenants Are Built Through the Deevnet API](/docs/architecture/decisions/tenant-model/0015-tenant-onboarding-through-api/) §12, [ADR-0017: How Tenant Code Reaches a Tenant Workload](/docs/architecture/decisions/tenant-model/0017-tenant-code-delivery/), [ADR-0025: Identity Directory](/docs/architecture/decisions/platform-services/0025-identity-directory/) §5, [CHG-0028](/docs/changes/2026/0028-tenant-workload-login/) |

---

## Context

A tenant can build a workload but cannot log in to it.

- **Every tenant workload trusts the substrate's automation key, with root.** The template tenant
  workloads clone is the substrate's Fedora template. Its kickstart creates `a_autoprov`, installs the
  shared automation public key and grants passwordless sudo, and cloud-init names `a_autoprov` again.
  The operator's automation credential therefore has root on every tenant VM, and ADR-0018 already
  records that as *"a defect, not accepted as a design"*.
- **A tenant's own keys never arrived.** The API accepts `ssh_keys` and the provider exposes it, but
  the API encoded the keys so that every space reached Proxmox as `+`, and Proxmox rejected them.
  No tenant key has ever landed on a workload.
- **The tenant developer network has no path to a workload.** `DVNTM-TD` reaches the API, the state
  store, the broker, the log store, Grafana and the downloads, and nothing in the tenant overlay.
- **So code reaches a workload only through the operator,** who logs in as `a_autoprov` and installs
  it. That is the only step in the tenant journey that is not self-service.

Fixing `ssh_keys` alone would make this worse: the tenant's key would join the automation key on the
same root-equivalent account.

## Decision

### 1. The tenant supplies a public key; the private key never leaves the tenant

`ssh_keys` on `deevnet_workload` carries public keys only. The substrate never generates, holds or
returns a private key for workload login. There is nothing to recover, rotate or leak on the
substrate's side, and nothing sits in Terraform state that would let someone else log in.

### 2. Keys land on a tenant account, not on `a_autoprov`

cloud-init creates one account from the site's setting (`tenant` on the mobile site), holding exactly
the keys the tenant declared. The account has passwordless sudo: the workload is the tenant's. The API
reports the account as the workload's `login_user`, so no page and no tenant has to guess it:

```
ssh <login_user>@<fqdn>
```

### 3. Tenant workloads clone a tenant template that carries no `a_autoprov`

The image factory builds two flavors of the Fedora template from one definition. Substrate VMs keep
cloning `fedora-server-*`, with `a_autoprov`. Tenant workloads clone `fedora-tenant-*`, whose build
removes `a_autoprov`, its key and its sudoers entry as its last step and fails if any trace remains.
The prefixes differ, so the API's "newest by prefix" can never pick the substrate template.

### 4. The operator has no standing access to a tenant workload

With no `a_autoprov` on the workload, the operator gets in only when the tenant adds the operator's
public key to `ssh_keys`, and loses access when the tenant removes it. ADR-0018's route stays, and
still gives the management and trusted networks a path to the overlay, but the path no longer implies
a credential. This answers ADR-0018's open question 3 in the tenant's favor.

### 5. A tenant developer reaches its workloads over SSH from `DVNTM-TD`

One rule: `tenant_dev` → the tenant overlay, TCP 22. Like every rule into the overlay it is
zone-level, because the core router sees the aggregate and not individual tenants. So what keeps
tenant A out of tenant B's workload is §1 to §3, not the network.

## Consequences

- **Self-service code delivery exists** for a person at a keyboard: `scp`, `rsync`, `git pull`,
  `podman`, whatever the tenant likes. ADR-0017 remains the answer for unattended delivery (a rebuilt
  workload filling itself), but it no longer blocks a tenant from shipping.
- **Existing workloads are rebuilt.** They were cloned from the substrate template and carry
  `a_autoprov`; nothing short of a new clone removes it.
- **A key change means a new workload.** Keys are written at first boot. The provider does not force
  replacement, so a key edit never destroys a VM without warning; the tenant replaces the workload
  when it means to.
- **A tenant who loses its private key loses access** to that workload. The recovery is a new key and
  a replaced workload, which is also why data belongs on a separate disk rather than the OS disk.
- **The operator can no longer help without being asked.** This is intended.
- **Two templates to keep current** instead of one.

## Alternatives considered

- **The API issues a keypair at tenant creation, like a Wi-Fi key.** Nothing hand-issued, but the
  private key would sit in Terraform state on a plain-HTTP, single-copy store, and would be one more
  secret class with no rotation. Rejected for now; a tenant that wants it can generate a key in its own
  Terraform with the `tls` provider.
- **Short-lived certificates from an OpenBao SSH CA** (ADR-0025 §5, extended to tenants). The right
  end state: expiry, a principal per tenant, an auditable operator principal. It needs an SSH engine,
  an API signing endpoint and template changes, and depends on ADR-0025. Nothing here stands in its
  way: a certificate-trusting template is a third flavor, and `ssh_keys` keeps working beside it.
- **Keep one template and strip `a_autoprov` with cloud-init at first boot.** It moves a security
  property from the image, where the build can prove it, to a boot-time script that can silently
  fail. Rejected.

## Open questions

1. **Should the tenant account's sudo be configurable per workload?** Not asked for yet.
2. **Should a tenant be able to replace keys without replacing the workload?** Proxmox regenerates
   the cloud-init drive on reconfigure. Whether the guest applies changed keys on its next boot is
   untested.
