---
title: "CHG-0040: Device Secrets in Tenant Code"
weight: -40
---

# CHG-0040: Device Secrets in Tenant Code

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Migration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Unscheduled. One API deploy, one provider release, then each tenant migrates on its own schedule |
| **Site** | mobile |
| **Systems** | `dv02prv001v01` (the Deevnet API); the provider; the tenant repositories of `eds` and `mabell`, and the reference tenant |
| **Automation** | `deevnet-provisioning-api`, `terraform-provider-deevnet`, each tenant's Terraform |
| **Risk** | Medium. Most likely to go wrong: a migration that changes a device's secret. Each tenant migrates the values it already holds, so no device sees a change |
| **Related changes** | [CHG-0013](/docs/changes/2026/0013-tenant-wifi-ppsk-keys/), [CHG-0016](/docs/changes/2026/0016-broker-accounts/) |
| **Related incidents** | None |
| **Related runbooks** | [Wi-Fi keys](/docs/runbook/tenant/services/wifi-keys/), [Devices and MQTT](/docs/runbook/tenant/services/devices-and-mqtt/), [Lost State or Credentials](/docs/runbook/tenant/recovery/lost-credentials/) |

---

## Summary

Today the API generates each device's broker password and Wi-Fi key, and the tenant's Terraform state is
their only lasting copy ([ADR-0012](/docs/architecture/decisions/tenant-model/0012-iot-platform-api/) §4).
Lose that state with the API's database and every device needs a visit.
[ADR-0033](/docs/architecture/decisions/tenant-model/0033-code-is-the-state/) decided the tenant's code
is the authoritative copy instead. This change builds it: the tenant supplies device secrets from its
own repository, encrypted, and passes them as write-only values that never land in state. It also
covers the state store's credentials, which ends the circle in which those keys sit inside the state
they unlock ([T2](/docs/architecture/reviews/2026-10-rebuild-and-access/#t2-state-key-recovery)).
Once a tenant has been rebuilt from its repository with no restore, ADR-0033 is accepted.

## Goal

- The provider's Wi-Fi key and broker account resources accept a tenant-supplied secret as a
  write-only argument; the API stores what it is given instead of generating one.
- A tenant's restore path supplies the secret from its configuration, not its state.
- The reference tenant shows the pattern: secrets in an `age`-encrypted file, decrypted at plan time.
- `eds` and `mabell` have moved their **existing** secrets into their repositories; no device was
  touched.
- A tenant rebuilt from its repository alone, with its state and the API's records deleted, comes
  back with its devices connecting. ADR-0033 is then Accepted.

## Scope

**In scope:** the API and provider changes; the reference tenant; migrating `eds` and `mabell`; the
state store's credentials kept in the tenant's repository.
**Out of scope:** device certificates (CHG-0034), which later replace broker passwords.

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A migration mints a new secret | a tenant | Export each current secret from state into the encrypted file first; the plan must show no change to the secret |
| Write-only arguments need a newer Terraform | tenants | Write-only arguments arrived in Terraform 1.11; the site runs 1.14; tenants' `required_version` is raised |
| Changing a tenant's repository without its owner | tenant repositories | Each tenant's change is a pull request in its own repository, reviewed by its owner |

## Prerequisites

- [ ] [CHG-0038](/docs/changes/2026/0038-reconcile-restores-everything/) complete (the reconcile and
      provider changes this builds on)
- [ ] Each tenant's owner agrees to its migration

## Procedure

### Step 1: The API and provider

Accept a supplied secret on create and on restore; make the secret attributes write-only; keep the
generated path for tenants not yet migrated.

**Verify:** integration tests for supplied, generated and restored secrets pass.

### Step 2: The reference tenant

Add the encrypted secrets file and the plan-time decryption to tdemo, and the guide pages that describe
it.

**Verify:** tdemo applies with a supplied secret, and its plan is clean afterwards.

### Step 3: Migrate eds and mabell

Per tenant: export the current secrets from state into the encrypted file, switch the resources to
supply them, apply.

**Verify:** the plan shows no change to any secret; the devices stay connected throughout.

### Step 4: The rebuild drill

On a throwaway tenant, or tdemo: delete its state and its API records, then rebuild from its repository.

**Verify:** its devices, or a test client holding its secrets, connect with no change. Mark ADR-0033
Accepted.

## Verification

Step 4 passes, and the recovery chart no longer lists "devices need re-provisioning" for a lost
provisioning VM.

## Undo

The generated path stays in the API, so a tenant can return to it; a migrated tenant's secrets are
the same values either way.

## To discover

- How the restore path should behave for a tenant with no secret in its configuration.
- Whether the state store's credentials belong in the same encrypted file or the backend's own
  configuration.
