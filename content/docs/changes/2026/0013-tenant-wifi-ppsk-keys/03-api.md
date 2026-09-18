---
title: "3. API"
weight: 3
---

# Phase 3: The API issues keys

Merged: `deevnet-provisioning-api` #9 (v0.3.0), `ansible-collection-deevnet.mgmt` #29.

**Blocked on the Owner** creating the API's own Open API client. Until then v0.3.0 deploys happily
with Wi-Fi keys off — that is deliberate, and tested.

## Run

1. **Owner, in the controller UI:** Global View → Settings → Platform Integration → Open API. Create
   a second client, separate from Ansible's.
2. Vault it as `vault_omada_api_client_id` / `vault_omada_api_client_secret` in
   `group_vars/network_controllers`.
3. In `mobile/group_vars/deevnet_api/vars.yml`, set `deevnet_api_omada_url` and add
   `omada_client_id` / `omada_client_secret` to `deevnet_api_backends`, read cross-group the way the
   router key already is.
4. Stage and deploy:

```bash
cd deevnet-provisioning-api && git tag v0.3.0 && make stage
cd ../ansible-collection-deevnet.mgmt && ansible-playbook playbooks/deevnet-api.yml
```

## Verify

```bash
curl -s https://api.mobile.deevnet.net/version            # v0.3.0
# operator token, against a scratch tenant:
curl -sk -H "Authorization: Bearer $OP" -X POST \
  https://api.mobile.deevnet.net/v1/tenants/tdemo/wifi-keys \
  -d '{"name":"scratch","trust_class":"iot"}'
```

- The response carries `ssid: DVNTM-IOT`, `vlan: 30` and a `psk`.
- The controller UI shows **one key** in the `DVNTM-IOT` profile, named `tdemo-scratch`, bound to
  VLAN 30.
- `DELETE` removes it, and the profile is empty again.
- **Grep the API logs for that `psk` and find nothing.**
- Restart the API and issue another key, to exercise a fresh token.

## Undo

Redeploy the previous `deevnet_api_version` (`v0.2.6`) and delete any test key from the profile.
Unsetting `deevnet_api_omada_url` alone is enough to stop the API issuing keys, without a rollback.

## The zone rule

`platform -> management` is **declared** in the inventory zone policy by this change, not applied —
the core router still passes everything, because CHG-0007 has never run. Declaring it now is the
point: when the zone policy is finally applied, an undeclared path would break key issuance as a
timeout inside a tenant's `terraform apply`.
