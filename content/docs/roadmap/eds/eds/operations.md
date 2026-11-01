---
title: "Operations and Secrets"
weight: 7
tasks_completed: 1
tasks_in_progress: 1
tasks_planned: 7
---
# Operations and Secrets

Keeping EdS's secrets and settings, and the dated work that keeps it running.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---
## Project Vision & Scope

Secrets kept encrypted beside the code, settings switched from the console, and nothing that expires unnoticed.

**In Scope**
- Secrets, settings, renewals

**Out of Scope**
- Patching the Pis' operating systems: routine operations

---

## Secrets 🔄

- 🔄 Hand-kept secrets encrypted with sops and age: the key and `secrets/` made; Discogs, Spotify's settings and the state store's keys still to move (EdS ADR-0037)
- ✅ Each Pi's iTunes pairing kept, so a new card starts paired (EdS ADR-0052)
- ⏳ The relay paired as "EdS relay" and kept (EdS ADR-0052)
- ⏳ A second recipient for the key, and a secret scan on every push (EdS ADR-0037)

---

## Renewals ⏳

- ⏳ Spotify's authorization, before 2027-04-09 (EdS CHG-0004)
- ⏳ The console's certificate, before 2027-11-01 (EdS CHG-0047)
- ⏳ The backend Pi's certificate, before 2027-10-28, by a new request (EdS CHG-0042)

---

## Hygiene ⏳

- ⏳ lightd and palette served over TLS (EdS CHG-0007)
- ⏳ The amplifier's tape selector cleaned (EdS INC-0004)
