---
title: "EdS Local Song Detection"
weight: 4
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 4
---

# EdS Local Song Detection

Naming what plays on the turntable by fingerprints made here, in place of a recognizer behind
someone else's unpublished endpoint (EdS ADR-0021). A project and repository of its own, to come;
named for now by what it does: local audio fingerprinting.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

A stub. Landmark fingerprinting, the kind of technique a phone's song recognition uses, indexed from
the owner's own rips: a few seconds heard on the turntable are matched against the owner's
collection, naming the edition owned, and nothing leaves the house. Open-source engines exist
(audfprint, Panako, Olaf, Dejavu).

**In Scope**
- An index of fingerprints made from the owner's rips, and matching a clip against it
- Records held only on vinyl, added to the index as they are captured (EdS Vinyl Capture)

**Out of Scope**
- Knowing what the owner holds: EdS Music Inventory
- The turntable driver itself, which asks a recognizer: "a WAV in, a name out" (EdS ADR-0021)

---

## Detection ⏳

- ⏳ Choose a fingerprinting engine, and whether one match holds across masterings
- ⏳ An index from the owner's rips, kept current as the library changes
- ⏳ A recognizer EdS's turntable driver can ask in place of today's
- ⏳ Vinyl-only records added from their captures
