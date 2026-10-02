---
title: "CHG-0032: The Appliances on Site Certificates"
weight: -32
---

# CHG-0032: The Appliances on Site Certificates

| | |
|---|---|
| **Date** | 2026-10-02 |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | **In progress.** Both hypervisors and the Omada controller serve site certificates and their clients verify them. The core router's certificate is imported; **left:** the operator chooses it in the router's GUI, then `site_verify_opnsense: true`. |
| **Window** | 2026-10-02, from the Builder |
| **Site** | mobile |
| **Systems** | `dv02hyp001p01`, `dv02hyp002p02` (Proxmox), `dv02cor002p01` (core router), `dv02nms001v01` (Omada controller), `dv02prv001v01` (the Deevnet API) |
| **Automation** | `deevnet.mgmt` `certs.yml`, `site.yml`; `deevnet.builder` `site_bootstrap_cert`, `proxmox_node_cert`; `deevnet.net` `opnsense_cert`, `opnsense-cert.yml`; inventory `site_verify_*`, `omada_tls_enabled` |
| **Risk** | Medium — the core router's GUI and API are one server, and a bad certificate there takes both down |
| **Related changes** | [CHG-0031](/docs/changes/2026/0031-site-root-ca/) (the root and its intermediates) |
| **Related runbooks** | [Certificates](/docs/runbook/substrate/certificates/) |

---

## Summary

Builds [ADR-0030](/docs/architecture/decisions/substrate/0030-site-certificate-hierarchy/) §3 and
§8 for the three appliances that still served their own certificates, and stops their clients
skipping verification:

- **The hypervisors and the core router** come up before OpenBao, so the bootstrap intermediate signs
  them on the control node.
- **The Omada controller** issues from OpenBao.

Each certificate names what the inventory says the host is called: its A record, every CNAME and
every address. The core router's also names every VLAN gateway.

Every mechanism is the product's own documented one:

| Device | Mechanism |
|---|---|
| Proxmox | `pvenode cert set` |
| Core router | the Trust API to import, then one manual GUI selection: OPNsense has no API for the GUI's certificate (operator's decision) |
| Omada | the container image's `/cert` mount |

Clients verify only when the inventory's per-device switch is on, and each switch was turned on only
after its device verified.

## Goal

- Each appliance presents a site certificate that verifies against the root by every name, CNAME and
  address clients dial:
  - hypervisors `:8006`;
  - the controller `:8043`/`:8843`;
  - the router `:443`.
- The Deevnet API runs with `PROXMOX/OMADA/OPNSENSE_INSECURE_TLS=false`, and `make reconcile
  NAME=--all` succeeds.
- These all verify:
  - Ansible: `proxmox_vm`, `vm_identity`, `shutdown.yml`, `proxmox_node_network`, the `opnsense_*`
    roles and the Omada playbooks;
  - Packer;
  - the tenant fabric.
- A second `certs.yml` changes nothing.

## Procedure

1. **Merge and publish.** API #24, inventory #65, builder #23, net #44, mgmt #62; `make publish`
   (builder, net), `make install-dev` (mgmt). Every switch off: nothing live changed.
2. **hv02.** `certs.yml --tags hypervisors --limit dv02hyp002p02`.
3. **hv01.** The same, then `site_verify_proxmox: true` (inventory #66), redeploy the API, and merge
   Packer (image-factory #22) and the fabric (tenant-fabric #16).
4. **The controller.** `omada_tls_enabled: true` (inventory #67), `site.yml --limit dv02nms001v01`;
   then `site_verify_omada: true` (inventory #68) and redeploy the API.
5. **The router.** Back up its configuration, then `opnsense-cert.yml`. **Then the operator chooses
   the certificate in the GUI** ([Core Router](/docs/runbook/substrate/certificates/core-router/)),
   then `site_verify_opnsense: true` and redeploy the API.
6. `certs.yml` twice.

Rollback for each device is in its runbook page.

## Outcome

**Hypervisors.** Both nodes serve the leaf plus `Deevnet mobile bootstrap CA`, valid to 2027-10-02,
and verify by name, CNAME and address:
- hv01: `dv02hyp001p01`, `pve`, `10.20.99.21`.
- hv02: `dv02hyp002p02`, `pve2`, `10.20.99.22`.

A rerun is `changed=0`, which proves the role's name comparison. The rollback was rehearsed on hv02:
`pvenode cert delete 1` brought back the node's own certificate, and the role reinstalled the site
one. With verification on:
- `make reconcile NAME=--all` reconciled all four tenants;
- the `vm-identity.yml` survey passed;
- the fabric's `terraform plan` showed no changes.

**Controller.** Both 8043 and 8843 serve leaf, intermediate and root, and verify by
`omada.mobile.deevnet.net`, `dv02nms001v01…`, `localhost`, `10.20.99.40` and `127.0.0.1`. The role
took a copy of the controller's own keystore first (`eap.keystore.pre-chg0032`). The AP
`dv02wap001p01` stayed connected, checked through the Open API over verified TLS. A rerun does not
restart the controller. With verification on, the API reconciled every tenant (Wi-Fi keys through the
controller), and the playbooks' first call (`https://localhost:8043/api/info` from nms) verifies.

**Router.** Configuration backed up first: `migration-logs/dv02cor002p01-pre-chg0032-20261002T180721Z.xml`
(0600); the newest revision was `config-1790684723.1404.xml`. The Trust API now holds:
- `Deevnet mobile root CA`;
- `Deevnet mobile bootstrap CA`, linked to the root;
- `Deevnet site certificate (dv02cor002p01.mobile.deevnet.net)`, linked to the bootstrap CA, EKU
  serverAuth, valid to 2027-10-02. It names `dv02cor002p01`, `dns`, `dhcp` and `gateway`, and all ten
  gateway addresses.

A rerun imports nothing. The GUI still serves its own certificate, `Web GUI TLS certificate`, which
**expired on 2025-04-09**.

### Departures from the plan

- **`omada-wireless.yml --check` cannot run.** Its first `uri` task is skipped in check mode, so the
  next task has nothing to read. That predates this change. Instead, its first request was made from
  nms with verification on.
- **No firmware upgrade has run through 8043** against the site certificate. Untested.

## Follow-ups

- **The router's GUI selection**, then `site_verify_opnsense: true`, the API redeploy, and
  `opnsense.yml` with verification. Then mark this record Complete in both indexes.
- **The first router renewal** confirms the Trust API replaces a certificate in place
  (`trust/cert/set`); the role's read-back proves it either way.
- **Release the API** with `*_INSECURE_TLS` defaulting to off (API #24, merged).
- **Make `omada-wireless.yml` check-mode safe.**
- **Watch the first AP firmware upgrade** through the controller.
