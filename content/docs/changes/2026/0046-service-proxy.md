---
title: "CHG-0046: Tenant-Facing Services on 443"
weight: -46
---

# CHG-0046: Tenant-Facing Services on 443, Through a Service Proxy

| | |
|---|---|
| **Date** | Unscheduled |
| **Change type** | Deployment · Configuration |
| **Classification** | Structural |
| **Status** | Planned |
| **Window** | Not set. Steps 3 and 4 each interrupt a host's tenant-facing services for about a minute |
| **Site** | mobile |
| **Systems** | `dv02obs001v01` (Grafana, the log store, the tenant downloads), `dv02prv001v01` (the Deevnet API, the state store, the backup job), `dv02msg001v01` (the log bridge), `dv02cor002p01` (the site resolver and the zone policy) |
| **Automation** | `deevnet.mgmt`: the new `service_proxy` role; the `grafana`, `victorialogs`, `tenant_downloads`, `minio`, `deevnet_api` and `log_bridge` roles; `site.yml` and `certs.yml`. `deevnet.net`: `dns.yml`, `opnsense.yml`, `segment-check.sh`. The `mobile` inventory |
| **Risk** | Medium. Most likely to go wrong: a service that moved to loopback while its host's proxy is not serving, which takes that service away from every tenant. The play order and each step's checks guard it |
| **Related changes** | [CHG-0045](/docs/changes/2026/0045-grafana-service-name/) (Grafana's service name, and why names are not per tenant), [CHG-0030](/docs/changes/2026/0030-state-store-tls/) (the state store's TLS, and its console follow-up), [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/) and [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (the ports this hides) |
| **Related incidents** | None |
| **Related runbooks** | [Before You Start](/docs/runbook/tenant/getting-started/before-you-start/), [Segment Check](/docs/runbook/substrate/network/segment-check/), [Build Verification](/docs/runbook/substrate/building-recovery/build-verification/) |

---

## Summary

Each tenant-facing service answers on its own port: Grafana `:3000`, the log store `:8427` and the
tenant downloads `:8443` on the observability store VM; the Deevnet API `:8080` and the state store
`:9000` on the provisioning VM. A tenant has to know all five.

This change builds [ADR-0036](/docs/architecture/decisions/platform-services/0036-service-proxy/).
Each of the two VMs gets a service proxy that listens on 443 and forwards by name to the service,
which moves to the host's loopback address. Tenants dial a name and no port. The old ports keep
answering, through the proxy, so nothing a tenant holds stops working.

## Goal

- Each of these returns its service, with a certificate that verifies against the Deevnet Root CA,
  from an operator network and from `DVNTM-TD`:
  `https://grafana.mobile.deevnet.net`, `https://logs.mobile.deevnet.net`,
  `https://downloads.mobile.deevnet.net`, `https://api.mobile.deevnet.net`,
  `https://tfstate.mobile.deevnet.net`.
- Each old address still returns its service: `grafana…:3000`, `dv02obs001v01…:8427`,
  `downloads…:8443`, `api…:8080`, `tfstate…:9000`.
- On both hosts, each service listens on `127.0.0.1` only, and the proxy on the host's segment
  address.
- A name a host does not serve gets no TLS handshake on 443.
- The state store's console on `:9001` is not reachable from any other host.
- The API hands a tenant `dashboard_url`, `log_endpoint` and the state endpoint with no port.
- From `DVNTM-IOT`, both hosts are still blocked on 443.

## Scope

**In scope:** the `service_proxy` role and its certificate; Grafana, vmauth, the tenant downloads
and MinIO on loopback over plain HTTP; the API on loopback, keeping its certificate; the `logs`
alias; two zone rules for 443; the addresses the API hands out; the log bridge's store address; the
tenant guide and the operator's check scripts.

**Out of scope:**
- retiring the old ports and their six zone rules
- the broker, which is not HTTP and is on another segment
- OpenBao, the tenant DNS server's API, the Omada controller and the artifact server, none of which
  tenants reach
- the take-home Pi image, which keeps the old port numbers
- rewriting the address held in existing tenants' Terraform backends

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| A service is on loopback and its proxy is not serving | every tenant of that host | The proxy's play runs last in the same run. Steps 3 and 4 are one host each, checked before the next |
| The proxy cannot bind a port a service still holds | the host being changed | Play order: every service's play comes before the proxy's. The proxy restarts until the port is free |
| The state store rejects signed requests through the proxy | every tenant's `terraform init` and plan | The proxy passes the name and port the client dialed unchanged. Step 4 runs a tenant's plan at the old address and at the new one |
| The API cannot reach the state store by its service name | tenant admission and removal | Step 4 creates and removes a state user through the API |
| Grafana's live channel or login breaks behind the proxy | tenants' browsers | Step 3 logs in and opens a dashboard at both addresses |
| The backup job still dials the state store over TLS | the next backup | Step 4 runs the `backup` tag with the others, and a backup |
| A tenant's data sources hold the log store's old address | tenants' dashboards | The old address keeps answering. A reconcile rewrites them |
| The two 443 rules admit more than intended | the tenant dev segment | A name outside the proxy's list is refused. Step 5 checks it from `DVNTM-TD` |
| Certificates for three services are deleted | Grafana, the log store, the downloads | Intended. Undo reissues them: the roles issue on any run |

## Prerequisites

- [ ] Pull requests merged: `deevnet.mgmt`, the inventory, `deevnet.net` (`segment-check.sh`)
- [ ] Vault decrypted, collections built
- [ ] A backup taken ([CHG-0039](/docs/changes/2026/0039-backup-to-an-attached-ssd/)), before the
  state store changes how it listens
- [ ] Tenants told that the ports are going away and that the old addresses keep working

## Procedure

### Step 1: Read what is there

Read-only.

**Run:**

```bash
dig @10.20.10.1 logs.mobile.deevnet.net

ssh dv02obs001v01 'sudo ss -tlnp'
ssh dv02prv001v01 'sudo ss -tlnp'

cd ansible-collection-deevnet.net
ansible-playbook playbooks/dns.yml --check
ansible-playbook playbooks/opnsense.yml
bash scripts/segment-check.sh DVNTM-TD      # from a client on DVNTM-TD
```

**Verify:**

1. `logs` does not resolve.
2. Each service listens on every address, on its own port; nothing listens on 443 on either host.
3. The DNS check run reports one alias to add.
4. The zone policy report shows two rules to add and no other drift.
5. The segment check passes as it stands.

**Undo:** nothing to undo.

### Step 2: The alias

Not disruptive.

**Run:**

```bash
ansible-playbook playbooks/dns.yml
```

**Verify:**

1. `dig @10.20.10.1 logs.mobile.deevnet.net` answers `NOERROR` with `10.20.25.22`.
2. A second run reports no change.

**Undo:** remove the alias from inventory and run the playbook with `-e dns_delete_unmanaged=true`.

### Step 3: The observability store

Interrupts Grafana, the log store and the downloads for about a minute.

**Run:**

```bash
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --limit dv02obs001v01 \
  --tags log-store,dashboards,tenant-downloads,service-proxy
```

**Verify:**

1. `ss -tlnp` on the host: Grafana, vmauth and the downloads server on `127.0.0.1`; the proxy on
   `10.20.25.22` at 443, 3000, 8427 and 8443.
2. The proxy's certificate names the host, `grafana`, `logs`, `downloads` and the address.
3. `curl --cacert <root>` returns each service at its name on 443, and at its old address.
4. A request to `https://dv02obs001v01.mobile.deevnet.net/` fails in the handshake.
5. A browser at `https://grafana.mobile.deevnet.net` logs in as a tenant, opens a dashboard that
   shows data, and its links carry no port. The same at `:3000`.
6. With a tenant's write token, a log line pushed to `https://logs.mobile.deevnet.net` is read back
   with its read token. A request with no token is refused with `401`.
7. A large download completes with the right checksum.
8. The retired certificate directories are gone from the host.
9. A second run changes nothing and restarts nothing.
10. Stop the proxy: items 3 and 5 fail. Start it: they pass.

**Undo:** revert the `deevnet.mgmt` change and run the same tags without `service-proxy`; each role
reissues its certificate and listens on its port again. Then stop and disable `service-proxy`.

### Step 4: The provisioning VM

Interrupts the API and the state store for about a minute.

**Run:**

```bash
ansible-playbook playbooks/site.yml --limit dv02prv001v01 \
  --tags tenant-state,deevnet-api,backup,service-proxy
```

**Verify:**

1. `ss -tlnp` on the host: MinIO on `127.0.0.1:9000` and `:9001`, the API on `127.0.0.1:8080`; the
   proxy on `10.20.25.20` at 443, 8080 and 9000.
2. The proxy's certificate names the host, `api`, `tfstate` and the address.
3. `curl --cacert <root> https://api.mobile.deevnet.net/readyz` returns `200`, and so does the same
   at `:8080`.
4. As a tenant, `GET` of its own record shows `dashboard_url`, `log_endpoint` and the state
   endpoint with no port.
5. `tdemo`'s `terraform init` and `terraform plan` succeed against its unchanged `:9000` backend
   and plan nothing but the changed addresses. With the port removed from the backend,
   `terraform init -reconfigure` and a plan succeed again.
6. A reconcile of `tdemo` through the API reports every step done, the state store's and the
   dashboards' included.
7. `:9001` is refused from the Builder.
8. `sudo deevnet-backup` on the host completes, and the archive verifies.
9. A second run changes nothing and restarts nothing.

**Undo:** revert the inventory's `minio_*` and `deevnet_api_*` values and run the same tags without
`service-proxy`; MinIO reissues its certificate and both publish on every address again. Then stop
and disable `service-proxy`.

### Step 5: The zone policy

Not disruptive: two rules are added, none changed.

**Run:**

```bash
cd ../ansible-collection-deevnet.net
ansible-playbook playbooks/opnsense.yml                         # the report
ansible-playbook playbooks/opnsense.yml -e firewall_apply=true
```

**Verify:**

1. The report shows two rules to add, `tenant dev -> provisioning services (https)` and
   `tenant dev -> observability services (https)`, and nothing else.
2. After the apply, a second report shows no drift.
3. From `DVNTM-TD`: `segment-check.sh DVNTM-TD` passes, with the five names on 443.
4. From `DVNTM-TD`: a name neither host serves is refused on 443, and `:9001` times out.
5. From `DVNTM-IOT`: `segment-check.sh DVNTM-IOT` passes, with both hosts blocked on 443.

**Undo:** remove the two rules from inventory and apply.

### Step 6: The log bridge

Restarts the bridge. Device log lines published in that moment are lost, as on any restart.

**Run:**

```bash
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --tags log-bridge
```

**Verify:**

1. The bridge's store address is `https://logs.mobile.deevnet.net`.
2. A device log line published to the broker appears in its tenant's device partition.

**Undo:** revert `log_bridge_store_url` and run the tag again.

### Step 7: Tenants are told

Not disruptive.

**Run:** merge the tenant guide's port-free addresses and the provider's scripts, stage the scripts
to the downloads, and tell each tenant. A tenant does nothing unless it wants the shorter addresses
in its own code: its next plan reads the new `dashboard_url` and `log_endpoint`, and its backend
keeps working as written.

**Verify:**

1. The tenant guide shows no port for any of the five services.
2. `tenant-check.sh` passes from `DVNTM-TD`.
3. The documentation site builds without warnings.

**Undo:** revert the guide and the scripts.

## Verification

Steps 2 to 6 pass, a zone policy report shows no drift, and
[Build Verification](/docs/runbook/substrate/building-recovery/build-verification/)'s service
checks pass at the new addresses.

## Undo

Each step's own undo, in reverse. Steps 3 and 4 are independent: one host can be put back while the
other stays. Nothing a tenant holds is removed at any point, because every old address answers
before, during a host's minute, and after.

## To discover

- Whether a container on the provisioning VM's podman network reaches the proxy at the host's own
  address on 443. The API's call to the state store depends on it.
- Whether Grafana's data sources, which hold the log store's host name and `:8427`, are rewritten
  to the service name by a reconcile or only on create.
- Whether anything else dials these services by an address this record does not list. The exit
  node's egress agent dials the API at `:8080`.

## Outcome

Not yet run.

## Follow-ups

- [ ] Retire the old ports: the proxy's legacy listeners, the six per-port tenant dev rules, and
  the egress agent's API address
- [ ] Decide whether the take-home Pi image moves to 443
  ([ADR-0036](/docs/architecture/decisions/platform-services/0036-service-proxy/) open question 2)
- [ ] Decide whether the identity VM's services get the same treatment (open question 3)
- [ ] Accept ADR-0036 when this change completes
