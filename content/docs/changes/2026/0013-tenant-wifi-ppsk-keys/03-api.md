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

## Outcome — ran 2026-09-18

**Deployed and issuing keys.** `GET /version` returns `v0.3.0` (commit `c7afbe9`), `readyz` reports
the database ok, and the deploy was `failed=0` with 14 changed tasks — including the KV secret
rewrite that gave the API its Omada credential.

Verified end to end against the live controller:

| Check | Result |
|---|---|
| `POST /v1/tenants/tdemo/wifi-keys` | `201`, `ssid: DVNTM-IOT`, `vlan: 30`, `status: ready`, 32-character psk |
| The key on the controller | `name=tdemo-scratch`, `vlan=30`, no MAC binding, and its psk matches what the API returned |
| `GET` the key | **no `psk` field** — only `secrets_stored: true` |
| Re-`POST` the same key | **identical psk**, so re-applying never strands a flashed device |
| A trust class the site does not serve | `400`, and the error names the one it does |
| The psk in the API logs | **absent** across every log line |

Both Open API clients report `expiresIn: 7200`.

**One check the site cannot make:** the rule that a key may not change trust class is not exercised
here, because this site serves only `iot` — the request is refused earlier, by the unknown-class
check. That guard stays covered by unit test alone until a second class is served.

## DEFECT: a profile cannot be taken back to zero keys

**Revoking a tenant's only key fails.** `DELETE /v1/tenants/{name}/wifi-keys/{key}` answers `502`
and the controller says:

```
errorCode -34044 (The PPSK Profile should have at least one PSK entry.)
```

**The controller is asymmetric about this.** Phase 2 proved it will *create* a profile with an empty
key list — `{"ppsk": []}` returned `errorCode 0`, and the profile sat empty and bound to the SSID
quite happily. But `delete-psk` refuses to remove the last entry. So an empty profile is a legal
*state* that this operation will not *reach*.

The API behaves correctly given the refusal: the backend step fails, the registry row is kept, and
the tenant gets a `502` naming the step. Nothing is left half-done. But the revocation the tenant
asked for did not happen, and **revocation is most of what a per-tenant key is for**.

This was only ever findable by running it. The spec says nothing about it; `DeletePSKsOpenApiVO`
documents `ppskNameList` with no mention of a minimum.

**Current state of the estate:** one key, `tdemo-scratch`, is left in the `DVNTM-IOT` profile,
because it cannot be deleted while it is the only one. No device holds it. It comes out as soon as
the fix ships.

**Candidate fixes, in preference order:**

1. **`modifyPPSKProfile` with the remaining keys** (an empty list when the last one goes). Simplest,
   and plausible given that creation accepts an empty list — but **untested**, and it is a
   read-modify-write over a list that holds *every* tenant's key, so a failure part-way could lose
   another tenant's. It would need serialising.
2. **Keep one unusable placeholder.** Add a placeholder key with a freshly generated psk that is
   never returned or stored, then delete the real one — so the profile never goes below one entry.
   Respects the controller's stated invariant whatever `modifyPPSKProfile` does, and self-cleans:
   issuing any real key removes the placeholder. Costs an oddly-named key visible in the UI.
3. **Delete the profile when it empties.** Rejected: the profile is inventory's
   ([ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) §6), and the API must not
   delete objects inventory declares.

Option 1 needs one write against the controller to settle. Until then the defect stands.

## Undo

Redeploy the previous `deevnet_api_version` (`v0.2.6`) and delete any test key from the profile.
Unsetting `deevnet_api_omada_url` alone is enough to stop the API issuing keys, without a rollback.

## The zone rule

`platform -> management` is **declared** in the inventory zone policy by this change, not applied —
the core router still passes everything, because CHG-0007 has never run. Declaring it now is the
point: when the zone policy is finally applied, an undeclared path would break key issuance as a
timeout inside a tenant's `terraform apply`.
