---
title: "1. Recon"
weight: 1
---

# Phase 1: Recon

**Read-only, unauthenticated, no writes.** Done 2026-09-18, before any code was written, because
three of its answers changed what the automation had to do.

## Run

```bash
curl -sk "https://10.20.99.40:8043/v3/api-docs/00%20All" -o omada-spec.json
```

1,856 paths, 3,360 schemas, controller 6.3.0.45. No credentials are needed: the spec endpoint is
unauthenticated, the same one `omada-wireless.yml`'s preflight already reads.

## Verify

The five questions below are answered, and each is written down here rather than inferred later.

## Undo

None. Nothing was written.

---

## What it settled

### The paths are not symmetrical

| Operation | Method | Path |
|---|---|---|
| `getPPSKProfiles` | GET | `…/sites/{siteId}/ppsk-profiles` (**plural**) |
| `createPPSKProfile` | POST | `…/sites/{siteId}/ppsk-profile` (**singular**) |
| `getPPSKProfileDetail` | GET | `…/ppsk-profile/{profileId}` |
| `addPSKsToPPSKProfile` | POST | `…/ppsk-profile/{profileId}/add-psk` |
| `deletePSKsToPPSKProfile` | POST | `…/ppsk-profile/{profileId}/delete-psk` |

Guessing them symmetrically would have failed the play's preflight assert — which is the assert
doing its job, but it is cheaper to read the spec.

### Idempotency is properly available

- `getPPSKProfileDetail` returns `ppsk[] = {name, psk, mac, vlan}` — **the keys, with their
  passwords in plaintext**.
- `deletePSKsToPPSKProfile` takes `{"ppskNameList": [...]}` — **names, not ids**.

So the API does a real read-before-write: leave a key alone when its password and VLAN already
match, delete-then-add only when they differ. No unconditional rewrite, so a converged key is never
briefly absent.

**The plaintext readback is a fact worth recording.** Any caller holding the site-write permission
that every PPSK write needs can read every tenant's key. That is why no tenant may hold that
credential, and why the substrate automation never calls this operation.

### The SSID list cannot resolve a profile — but the profile list can resolve an SSID

`SsidOpenApiVO` carries `band, broadcast, chooseDevices, description, guestNetEnable, id, name,
security, ssidId, vlanEnable, vlanId, vlanPoolIds` — **no `ppskSetting`**. `getSsidDetail` does carry
it, but needs a list-then-detail per SSID.

`getPPSKProfileDetail`'s *brief* sibling, `getPPSKProfiles`, returns `ssid[]` per profile — the SSIDs
bound to it. So the API resolves profile-from-SSID in **one** call, and never has to agree with
inventory about a profile's name. The SSID is what the tenant is told to join; the profile bound to
it is authoritative.

It also confirmed the list returns `security`, so the play's new drift check costs no extra request.

### A PPSK name may be 1 to 64 characters

`<tenant>-<label>` is at most 8 + 1 + 20 = 29. No naming change needed.

### Whether a profile may be created empty is *not* answerable from the spec

`PpskProfile` requires `ppsk` to be **present** but sets no `minItems`, so `{"profileName": "…",
"ppsk": []}` is schema-valid. Whether the controller accepts it is runtime behaviour, and the
running controller is ground truth, not the schema — as `ip-setting` already demonstrated in
CHG-0005.

Rather than spend a write to find out, the play handles both: it tries empty, and on a refusal
creates the profile with one random seed key and deletes that key by name in the same run. Same end
state; the seed never persists and is never reported.

**Settled by phase 2, 2026-09-18: this controller accepts an empty key list.** The fallback was
never exercised. It stays in the play anyway — that is one controller's behaviour at one firmware
level, not a documented guarantee.

## Two things the spec says that the controller may not mean

Recorded so nobody "fixes" them blind:

- **`pskSetting` is not required for `security: 4`** by the schema, and `securityKey` is documented
  as security-3 only. But CHG-0005 found the controller answers `errorCode -1`, with no message,
  unless the `versionPsk`/`encryptionPsk`/`gikRekeyPskEnable` block is sent anyway. The workaround
  stands.
- **`vlanId` "must be null" when `vlanSetting` is sent.** The play sends both, and the three live
  SSIDs were created that way. The controller tolerates it. Not changed.
