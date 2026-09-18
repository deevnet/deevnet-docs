---
title: "6. Close-out"
weight: 6
---

# Phase 6: Close-out

## Run

1. **Correct the pages this change makes wrong or newly right:**
   - `architecture/substrate/networking.md` — the Wireless section names no SSIDs and no security
     model. It should carry the four, and say that on `DVNTM-IOT` the key decides the VLAN.
   - `platforms/network/access-point/_index.md` — "SSID Design" lists `Management / IoT / Guest`,
     which is not this site, and points at a standard that documents neither. Replace with the four
     real SSIDs and the ownership line: inventory owns the SSID and the profile, the API owns the
     keys inside it.
   - `platforms/network/network-controllers/_index.md` — record the **second** Open API client and
     what it is for.
   - `runbook/recovery/console-recovery/wireless-ap.md` §6–7 — drop the standalone-UI and
     `make migration-omada-ssids` assumptions; recovery is `make wireless APPLY=1 ADOPT=1` then
     `make wireless APPLY=1`. The §7 check of `DVNTM-IOT` now actually works.

   That recovery page also gets the sentence that matters most operationally:
   **recovery does not re-issue tenant keys.** They survive an AP rebuild in the profile, and if the
   profile itself is lost each tenant runs `terraform apply` and gets the same key back — so no
   device visit. ADR-0012 §5, made concrete.

2. **Retire the superseded playbook.** `playbooks/migration/13-omada-ssids.yml` and its
   `migration-omada-ssids` Make target used undocumented `/api/v2` calls and are replaced by
   `make wireless` (CHG-0005 follow-up #2).

3. **Mark [ADR-0012](/docs/architecture/decisions/0012-iot-platform-api/) Accepted** — at close-out,
   not at the start: it is accepted once the thing it decides has been built and proven on the AP.

## Verify

- `hugo --minify` clean, no broken internal links.
- `make help` in `deevnet.net` shows `wireless` and no longer shows `migration-omada-ssids`.

## Undo

Revert the docs commit. Nothing operational depends on this phase.
