---
title: "The Stand and Its Light"
weight: 1
tasks_completed: 8
tasks_in_progress: 0
tasks_planned: 2
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

- ✅ The device draws its effects and owns gamma; it is sent scenes, never frames (EdS ADR-0001, ADR-0002)
- ✅ palette, then lightd, then the stand: colors from the cover, chroma and gamut handled in lightd (EdS ADR-0009, CHG-0001, CHG-0003)
- ✅ The stand reports what it shows; `chase` and `morph`; 18 LEDs (EdS CHG-0008, CHG-0009, CHG-0010)
- ⏳ Effects checked on real LEDs; `morph` blends in RGB; an accent too close to the dominant color (EdS CHG-0009, CHG-0010)

---

## Looks ✅

- ✅ An album's own look, named by nowplayd and drawn by lightd (EdS ADR-0019)
- ✅ One track's look from any source: Knight Rider's `scanner` (EdS ADR-0030)
- ✅ Dark until sent a scene; red blinks say how far it got (EdS ADR-0029)

---

## Which sources light it 🔄

- ✅ Records only, dim while the turntable is on (EdS ADR-0028)
- ✅ The console switches it to every source, and back (EdS ADR-0039)
- ⏳ Lights for iTunes as their own thing, not the record's
