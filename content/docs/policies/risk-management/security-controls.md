---
title: "Security Controls"
weight: 2
---

# Security Controls

The controls that bound what a mistake or a compromise can reach. Each is summarised here with the
record that decided or built it; the design itself lives in those records.

---

## Network segmentation

The site network is split into zones by trust — management, trusted, platform, storage, tenant
transit, IoT, IoT vendor and guest
([Network Segmentation](/docs/architecture/network-segmentation/)).

- **Default deny between zones.** The core router allows only the inter-zone flows that are
  declared in inventory, and removes anything it did not declare
  ([CHG-0007](/docs/changes/2026/0007-core-router-zone-policy/))
- **Joining a network is not authorisation.** A device on the IoT network still needs a credential
  for every service it uses
  ([ADR-0020](/docs/architecture/decisions/0020-direct-device-access-to-tenant-services/))
- **Guest is internet-only**; IoT reaches the broker and the internet, not tenant workloads or
  management

## Tenant isolation

- **A routing domain per tenant.** Tenants are separated by VRF, not by a firewall rule — there is
  no route between them to filter ([ADR-0001](/docs/architecture/decisions/0001-tenant-network-fabric/))
- **Every tenant-facing service is partitioned by the platform, not by the tenant.** DNS updates are
  bound to the tenant's own zone by server-side key metadata; MQTT topics are prefixed by the API;
  log partitions are selected by the proxy from routes the API wrote. A tenant cannot claim another
  tenant's identity in a payload
- **Tenants hold no substrate credential** — one API token, nothing else
  ([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/))

## Encryption

| | In transit | At rest |
|---|---|---|
| The Deevnet API | TLS, site CA | registry secrets in OpenBao |
| MQTT broker | TLS only; no plaintext listener | — |
| Log store | TLS through an authenticating proxy | on the observability VM's disk |
| Substrate secrets | — | ansible-vault in the inventory; OpenBao for runtime secrets ([ADR-0016](/docs/architecture/decisions/0016-substrate-secrets-openbao/)) |
| Terraform state store | **plain HTTP today** — see the [register](/docs/policies/risk-management/risk-register/) | on one disk |
| Wi-Fi | WPA2 with a per-tenant key (PPSK) on the IoT SSID | — |

The site runs its own certificate authority; clients trust `site-ca.pem` rather than a public CA,
because nothing Deevnet serves is public.

## Credentials

- **Automation uses one account, by key.** `a_autoprov`, SSH key only, passwordless sudo, provisioned
  by the image factory. No passwords in playbooks or inventory
- **Secrets are encrypted before they are committed**, and a pre-commit hook refuses a plaintext
  vault
- **A credential a change generates is encrypted, committed and pushed before its source is
  deleted.** Losing one has cost a rebuild
  ([INC-0003](/docs/incidents/2026/0003-openbao-credential-loss/))
- **Tenant credentials are issued, not chosen**, and the tenant's own state is their authoritative
  copy; the API keeps hashes where it can
- The long-term direction — short-lived credentials, identity held by the client — is the
  [Secure Identity Standard](/docs/standards/secure-identity/)
