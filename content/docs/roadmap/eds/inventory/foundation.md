---
title: "Foundation and Collecting"
weight: 1
waypoints:
  - title: "Music inventory built as Go services with a SQLite store (eds-inventory ADR-0001)"
    group: "Foundation"
    status: done
    date: "2026-10-24"
  - title: "Music inventory's documentation and records started"
    group: "Foundation"
    status: done
    date: "2026-10-24"
  - title: "Music inventory collects the iTunes library from its XML (eds-inventory ADR-0002)"
    group: "Sources"
    status: done
    date: "2026-10-24"
  - title: "Music inventory collects the vinyl from Discogs"
    group: "Sources"
    status: planned
  - title: "Music inventory collects the MusicBee library"
    group: "Sources"
    status: planned
  - title: "Music inventory collects albums saved in Spotify and Tidal"
    group: "Sources"
    status: planned
  - title: "Music inventory covers formats with no service, such as CDs"
    group: "Sources"
    status: planned
  - title: "Music inventory matches one album across sources, and handles matches it is not sure of"
    group: "Sources"
    status: planned
---
# Foundation and Collecting

The service, its store, and the sources it collects.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---
## Project Vision & Scope

One inventory that keeps itself in step with every place the owner's music is kept.

**In Scope**
- The service and its store
- Each source, collected

**Out of Scope**
- Changing a source: each source stays the truth for what it holds

---

## Foundation ✅

{{< waypoints group="Foundation" >}}

---

## Sources 🔄

{{< waypoints group="Sources" >}}
