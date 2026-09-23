---
title: "Build Tenants"
weight: 20
---

# Build Tenants

How a tenant is created on the mobile substrate today: the operator admits a name, and the tenant
declares everything else through the Deevnet API
([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/)).

Two people, two credentials, and nothing hand-allocated. The operator never edits an inventory file
to make a tenant, and the tenant never holds a Proxmox credential, a vault password or an index.
The older procedure that did those things is
[Provisioning a Tenant](/docs/runbook/tenant-provisioning/), kept only as history — its mechanisms
have been removed.

---

## Before you start

**Operator side:**

| | |
|---|---|
| The API | `https://api.mobile.deevnet.net:8080`, reachable from the Builder |
| The operator token | `vault_deevnet_api_token`, in the inventory's `deevnet_api` group vault |
| The site CA | `ansible-collection-deevnet.mgmt/.openbao/site-ca.pem` on the control node |

**Tenant side:**

| | |
|---|---|
| Terraform | 1.5 or later |
| The provider | `deevnet/deevnet`, from the filesystem mirror at `~/.terraform.d/plugins/registry.terraform.io/deevnet/deevnet/` |
| The site CA | the same file, copied into the tenant directory as `site-ca.pem` |

The provider is not on a public registry. It is built from
[`terraform-provider-deevnet`](/docs/github/) and mirrored by the workstation role; a tenant that
cannot `init` usually needs the mirror updated, not the internet.

{{< hint info >}}
**Check the provider version before a tenant's first apply.** A tenant only receives what the
provider it initialised with knows how to read. A tenant created against 0.2.x, for instance, never
saw its log store tokens, and had to be reconciled afterwards to get them.
{{< /hint >}}

---

## 1. Admit the name (operator)

```bash
curl -sS --cacert site-ca.pem \
  -H "Authorization: Bearer $OPERATOR_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"mabell"}' \
  https://api.mobile.deevnet.net:8080/v1/admissions
```

```json
{ "name": "mabell", "enrollment_token": "s.…", "expires_at": "2026-09-26T…Z" }
```

| | |
|---|---|
| The name | `^[a-z][a-z0-9]{0,7}$` — it becomes a PVE SDN zone ID, a DNS label and a state-store user |
| The token | single-use, expires after `DEEVNET_ENROLLMENT_TTL` (72h by default) |
| A name already registered | answers `409`. Admission creates nothing; it only authorises |

Deliver the token to the tenant age-encrypted ([ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §9).
Presenting it for a different name **spends** it and answers `401`.

---

## 2. The tenant's Terraform

A tenant is code in its own repository
([ADR-0006](/docs/architecture/decisions/0006-tenant-code-boundary/)). When the tenant exists to
serve one application, that repository can be the application's own — EdS and Ma Bell both keep
`infra/deevnet-tenant-<name>/` beside their firmware, so the device and the infrastructure it
depends on stay together.

The minimum is one resource:

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    deevnet = { source = "deevnet/deevnet", version = "~> 0.3" }
  }
}

# DEEVNET_API_ENDPOINT, DEEVNET_API_TOKEN, DEEVNET_API_CACERT
provider "deevnet" {}

resource "deevnet_tenant" "this" {
  name = "mabell"
}
```

Everything else — workloads, DNS records, Wi-Fi keys, devices, broker accounts — derives from the
index the API allocates, and is added in the same configuration.

**A tenant needs no workload.** A device-only tenant (Ma Bell) declares a Wi-Fi key, a device and a
broker account and nothing else. A VM that nothing runs on costs memory on the tenant hypervisor
and proves nothing.

---

## 3. First apply

```bash
export DEEVNET_API_ENDPOINT=https://api.mobile.deevnet.net:8080
export DEEVNET_API_CACERT=$PWD/site-ca.pem
export DEEVNET_API_TOKEN=<the enrollment token>

terraform init
terraform plan
terraform apply
```

The apply spends the enrollment token and the API allocates an index. **From the second apply
onward the credential is the tenant's own token**, which is an output:

```bash
export DEEVNET_API_TOKEN=$(terraform output -raw api_token)
```

{{< hint warning >}}
**The state file now holds every credential the tenant was issued**, and for most of them it is the
authoritative copy ([ADR-0015](/docs/architecture/decisions/0015-tenant-onboarding-through-api/) §4).
Never commit it. Losing it means asking the API to restore what it can, and re-issuing the rest —
which for a device means reflashing it.
{{< /hint >}}

---

## 4. What the substrate did

| | |
|---|---|
| Network | an EVPN zone and VRF on the tenant hypervisor, one VNet, a `/24` from `10.20.128.0/18`, anycast `.1`, SNAT at the exit node |
| DNS | `<tenant>.<site>.deevnet.net` and its reverse, delegated, with a TSIG key the tenant writes records with |
| State | a bucket and keys in the state store |
| Logs | partitions `(index, 0..2)`, an ingest and a read token, and the vmauth routes that separate them from every other tenant ([ADR-0027](/docs/architecture/decisions/0027-tenant-log-store/)) |
| Devices, if declared | a PPSK per trust class, registry entries, and MQTT accounts confined to the tenant's own topic prefix |

The index is the tenant's number in all of it — subnet, VXLAN VNI, log account — so it is allocated
once, against both the registry **and** the live fabric, and never by hand.

---

## 5. Move the state into the store

Optional, and worth doing once the tenant matters:

```bash
make state-backend                 # prints the backend block and the access key
# uncomment the backend block in main.tf with those values
export AWS_ACCESS_KEY_ID=… AWS_SECRET_ACCESS_KEY=…
terraform init -migrate-state
```

---

## 6. Verify

The full list is [Verify Tenants](/docs/runbook/building-recovery/verify-tenants/). The four checks
worth running on every new tenant:

```bash
terraform plan -detailed-exitcode      # 0: the declaration and the substrate agree
```

- **The fabric:** `pvesh get /cluster/sdn/zones` on the tenant hypervisor shows `vrf_<tenant>` with
  its own VNI.
- **Names:** a record the tenant writes resolves through the tenant resolver.
- **Logs:** the tenant's ingest token writes a line and its read token reads it back — and another
  tenant's read token, pointed at this tenant's partition, returns nothing.

---

## Removing a tenant

`terraform destroy` with the tenant's own token. It removes the fabric, the DNS zone, the workloads
and the tenant's registry row, and revokes its tokens.

What it does **not** remove is anything outside the API's reach: logs already written stay until
retention expires, and a device already flashed keeps a key that no longer authenticates. Destroy
and recreate therefore issues new device credentials — the device has to be reflashed.

---

## When it goes wrong

| Symptom | What it means |
|---|---|
| `No API token` from the provider | `DEEVNET_API_TOKEN` is not exported in *this* shell. The Makefile's `require-token` catches it earlier |
| `Saved plan is stale` | the state moved between `plan` and `apply`. Re-plan, or apply directly |
| `409` on admission | the name is already registered. Use the tenant's own token, not a new admission |
| `401` on the first apply | the enrollment token was issued for a different name, and is now spent |
| A tenant lists with no log store | the list endpoint returns lean records. Ask the detail endpoint before concluding anything is missing |
| `501` on every tenant route | the API has no site configured, or no OpenBao |
