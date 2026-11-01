---
title: "Operations and Secrets"
weight: 7
milestones:
  - title: "Hand-kept secrets encrypted with sops and age: the key and `secrets/` made; Discogs, Spotify's settings and the state store's keys still to move (EdS ADR-0037)"
    group: "Secrets"
    status: active
  - title: "Each Pi's iTunes pairing kept, so a new card starts paired (EdS ADR-0052)"
    group: "Secrets"
    status: done
    date: "2026-10-29"
  - title: "The relay paired as \"EdS relay\" and kept (EdS ADR-0052)"
    group: "Secrets"
    status: planned
  - title: "A second recipient for the key, and a secret scan on every push (EdS ADR-0037)"
    group: "Secrets"
    status: planned
  - title: "Spotify's authorization, before 2027-04-09 (EdS CHG-0004)"
    group: "Renewals"
    status: planned
  - title: "The console's certificate, before 2027-11-01 (EdS CHG-0047)"
    group: "Renewals"
    status: planned
  - title: "The backend Pi's certificate, before 2027-10-28, by a new request (EdS CHG-0042)"
    group: "Renewals"
    status: planned
  - title: "lightd and palette served over TLS (EdS CHG-0007)"
    group: "Hygiene"
    status: planned
  - title: "The amplifier's tape selector cleaned (EdS INC-0004)"
    group: "Hygiene"
    status: planned
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

{{< milestones group="Secrets" >}}

---

## Renewals ⏳

{{< milestones group="Renewals" >}}

---

## Hygiene ⏳

{{< milestones group="Hygiene" >}}
