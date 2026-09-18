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

## Outcome — ran 2026-09-18

Done, with one departure from the plan.

**Departure: the architecture page was NOT given the SSID names.** The close-out above said to list
the four SSIDs on `architecture/substrate/networking.md`. That conflicts with the documentation
convention — architecture pages are implementation-agnostic, and naming `DVNTM-IOT` there breaks it.
So that page gained the *model* instead: one SSID per trust class, per-credential keys on the device
segments so the key decides the VLAN, keys issued per owner and never choosing a VLAN. The concrete
names, VLANs and security modes went to the access point page, which is the implementation-specific
home for them.

| Page | What changed |
|---|---|
| `architecture/substrate/networking.md` | the model, kept generic; points at the AP page for names |
| `platforms/network/access-point/_index.md` | the real four SSIDs with security model and key ownership, the per-key VLAN fact, and the placeholder entry an operator will see |
| `platforms/network/network-controllers/_index.md` | documented Open API not the internal one, `make wireless`, **the two Open API clients and why**, and that the event log records device events but not client associations |
| `runbook/recovery/console-recovery/wireless-ap/` | §6 is `make wireless`, not the standalone UI; §7 notes `DVNTM-IOT` needs a tenant's key to test; and **recovery does not re-issue tenant keys** |
| `changes/2026/0001-…/port-migration.md` | annotated, not rewritten: the retired command stays as a record of what was run, with a pointer to `make wireless` |
| CHG-0005 follow-ups | both ticked, with a note that the keys turned out per-tenant rather than per-device from inventory |
| ADR-0012 | **Accepted**, with a Current state that separates what is built from what is not |

`playbooks/migration/13-omada-ssids.yml`, its Make target, its `.PHONY` entry and its help line are
gone. `make help` shows `wireless` and no longer mentions omada migration.

## Verify

- `hugo --minify` clean, no broken internal links: 223 pages.
- `make help` in `deevnet.net` shows `wireless` and no longer shows `migration-omada-ssids`.

## Undo

Revert the docs commit, and `git revert` the playbook removal. Nothing operational depends on this
phase — `make wireless` was already the live path before the old playbook was deleted.
