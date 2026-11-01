---
title: "Screens and Console"
weight: 3
tasks_completed: 4
tasks_in_progress: 0
tasks_planned: 2
---
# Screens and Console

The console a person looks at, and the cover screen beside the stand that pauses, skips and sets the volume.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---
## Project Vision & Scope

What is playing, what the stand shows and whether the parts are up, in one place; a few controls by the stand.

**In Scope**
- The console and its two settings
- The cover screen

**Out of Scope**
- Controls that change what plays from the console: a decision first, with a login

---

## Console 🔄

- ✅ The console, over TLS, looking at everything (EdS ADR-0018)
- ✅ Named site-less too: `console.eds.deevnet.net` beside the factory's name (EdS CHG-0047)
- ⏳ Covers sent at full size; recently played lost on restart; strip length told, not reported (EdS CHG-0006, CHG-0010)

---

## Cover screen 🔄

- ✅ Cover, play/pause, skip and volume by touch (EdS ADR-0020)
- ✅ Sleeps when nothing has played for five minutes (EdS ADR-0036)
- ⏳ Why its first start after a provisioning write sent no presses (EdS CHG-0042)
