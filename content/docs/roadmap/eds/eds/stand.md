---
title: "The Stand and Its Light"
weight: 1
waypoints:
  - title: "The LP stand draws its own light effects and handles gamma; it is sent scenes, never frames (EdS ADR-0001, ADR-0002)"
    group: "Light from the cover"
    status: done
    date: "2026-09-07"
  - title: "The LP stand's colors come from the album cover: one service finds them, another makes the scene, the stand draws it (EdS ADR-0009, CHG-0001, CHG-0003)"
    group: "Light from the cover"
    status: done
    date: "2026-10-11"
  - title: "The LP stand reports what it shows, with `chase` and `morph` effects on 18 LEDs (EdS CHG-0008, CHG-0009, CHG-0010)"
    group: "Light from the cover"
    status: done
    date: "2026-10-11"
  - title: "The LP stand in service, its effects seen on real LEDs (EdS CHG-0009, CHG-0010)"
    group: "Light from the cover"
    status: done
    date: "2026-10-11"
  - title: "LP stand color fixes: `morph` blends in RGB, and an accent can sit too close to the dominant color (EdS CHG-0009, CHG-0010)"
    group: "Light from the cover"
    status: planned
  - title: "Particular albums get their own light on the LP stand (EdS ADR-0019)"
    group: "Looks"
    status: done
    date: "2026-10-11"
  - title: "A particular track gets its own light on the LP stand from any source, such as a `scanner` effect for Knight Rider (EdS ADR-0030)"
    group: "Looks"
    status: done
    date: "2026-10-13"
  - title: "The LP stand stays dark until sent a scene, and red blinks say how far it got (EdS ADR-0029)"
    group: "Looks"
    status: done
    date: "2026-10-13"
  - title: "The LP stand lights for records only, and is dim while the turntable is on (EdS ADR-0028)"
    group: "Which sources light it"
    status: done
    date: "2026-10-13"
  - title: "The EdS console switches the LP stand between records only and every source (EdS ADR-0039)"
    group: "Which sources light it"
    status: done
    date: "2026-10-19"
  - title: "A printed circuit board for the LP stand"
    group: "Hardware"
    status: planned
  - title: "A permanent enclosure for the LP stand"
    group: "Hardware"
    status: planned
---
# The Stand and Its Light

An LP jacket stand lit by an RGB strip from the record's cover: palette finds the colors, lightd makes them a scene, the stand draws it.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---
## Project Vision & Scope

The stand follows the record that is playing and draws its own effects; nothing streams frames to it.

**In Scope**
- Colors from the cover, effects on the device, looks for particular albums and tracks
- Which sources light the stand

**Out of Scope**
- What is playing and its cover: Now Playing

---

## Light from the cover 🔄

{{< waypoints group="Light from the cover" >}}

---

## Looks ✅

{{< waypoints group="Looks" >}}

---

## Which sources light it ✅

{{< waypoints group="Which sources light it" >}}

---

## Hardware ⏳

{{< waypoints group="Hardware" >}}
