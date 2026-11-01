---
title: "Operations and Secrets"
weight: 7
milestones:
  - title: "EdS's hand-kept secrets encrypted with sops and age: the key and `secrets/` made; Discogs, Spotify's settings and the state store's keys still to move (EdS ADR-0037)"
    group: "Secrets"
    status: active
  - title: "Each Pi's iTunes pairing kept, so a new SD card starts paired (EdS ADR-0052)"
    group: "Secrets"
    status: done
    date: "2026-10-29"
  - title: "EdS's relay Pi paired with iTunes as \"EdS relay\", and the pairing kept (EdS ADR-0052)"
    group: "Secrets"
    status: planned
  - title: "A second recipient for EdS's secrets key, and a secret scan on every push (EdS ADR-0037)"
    group: "Secrets"
    status: planned
  - title: "EdS's Spotify authorization renewed before 2027-04-09 (EdS CHG-0004)"
    group: "Renewals"
    status: planned
  - title: "The EdS console's certificate renewed before 2027-11-01 (EdS CHG-0047)"
    group: "Renewals"
    status: planned
  - title: "The certificate on the Pi that runs EdS's back end renewed by a new request before 2027-10-28 (EdS CHG-0042)"
    group: "Renewals"
    status: planned
  - title: "EdS's lighting and color-finding services served over TLS (EdS CHG-0007)"
    group: "Hygiene"
    status: planned
  - title: "The stereo amplifier's tape selector cleaned (EdS INC-0004)"
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
