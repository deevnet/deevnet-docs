---
title: "Serving EdS"
weight: 4
waypoints:
  - title: "Music inventory runs on EdS's workload, beside its voice service (eds-inventory ADR-0003)"
    group: "Clients"
    status: done
    date: "2026-10-24"
  - title: "EdS's voice service asks the music inventory for artists and albums (EdS ADR-0047)"
    group: "Clients"
    status: done
    date: "2026-10-24"
  - title: "EdS's now-playing service asks the music inventory for a track's album, cover and original (EdS music-inventory proposal)"
    group: "Clients"
    status: planned
  - title: "Music inventory also runs on EdS's Pi at home"
    group: "Where it runs"
    status: planned
---
# Serving EdS

What EdS asks the inventory, and where the inventory runs.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---
## Project Vision & Scope

EdS asks the inventory, and the inventory alone, about the owner's music.

**In Scope**
- voiced's and nowplayd's questions
- Where it runs

**Out of Scope**
- Hearing anything: EdS's recognizer stays EdS's

---

## Clients 🔄

{{< waypoints group="Clients" >}}

---

## Where it runs ⏳

{{< waypoints group="Where it runs" >}}
