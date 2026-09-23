---
title: "Traceability"
weight: 3
---

# Traceability

Every configuration choice in Deevnet should be explainable from records: **why** it was decided,
**what** was changed to make it so, and **what happened** when it went wrong. Traceability is a risk
control — the risk it treats is a future operator (often the same person, months later) undoing a
deliberate choice because nothing said it was deliberate.

---

## The chain

{{< mermaid >}}
graph LR
    A[ADR<br>why] --> B[Change record<br>what, and how to undo it] --> C[Pull requests<br>the code]
    B --> D[Incident record<br>what it cost, if it failed]
    D --> A
{{< /mermaid >}}

| Record | Answers | Numbered | Lives in |
|---|---|---|---|
| **ADR** | why this design, what else was considered, what it costs | `ADR-NNNN` | [Decisions](/docs/architecture/decisions/) |
| **Change record** | what was changed, the end state, the procedure, the undo, what actually happened | `CHG-NNNN`, by year | [Change Records](/docs/changes/) |
| **Incident record** | what broke, how it was found, why, what prevents a repeat | `INC-NNNN`, by year | [Incident Records](/docs/incidents/) |
| **Pull request** | the exact code, reviewed and merged | per repository | GitHub |

## The rules

- **Every significant change has a record**, opened before the change, closed with the outcome —
  including what was *not* tested ([Change Management](/docs/policies/change-management/))
- **Every incident has a record**, even when the change that caused it already has one
  ([Incident Management](/docs/policies/incident-management/))
- **Records link both ways.** A change names the ADR it implements and the PRs that carry it; an
  incident names the change that caused it and the changes that fix it
- **Index pages are updated in the same commit** as the record whose state changed, so the list and
  the record never disagree
- **Numbers are never reused**, and a superseded ADR stays, marked superseded, so the reasoning that
  led to today is still readable
- **Standards and ADRs win over code.** If a repository conflicts with them, the repository is the
  defect

## Using it

"Why does the router drop this?" → the rule is in inventory → its commit → the PR → the change
record → the ADR. If any link is missing, that is worth a follow-up, because the next person asking
will not have the context you have now.
