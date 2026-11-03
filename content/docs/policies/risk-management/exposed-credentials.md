---
title: "Exposed Credentials"
weight: 3
---

# Exposed Credentials

What makes a credential exposed, how soon an exposed one is replaced, and what is recorded. An
exposed credential is a risk with one treatment, rotation, and this page sets how quickly it is
applied. Which credentials exist, what each reaches and how each is rotated are in the
[Credential Rotation](/docs/roadmap/infrastructure/substrate/credential-rotation/plan/) plan.

---

## What counts as exposed

**A credential is exposed when a copy may exist anywhere it was not issued to.** Whether anyone
has used the copy does not matter. Each of these makes a credential exposed:

- it was committed or pushed unencrypted, to any repository, even if the commit was reverted or
  the history rewritten
- it was printed, pasted or written outside the vault and the systems it was issued to: a
  terminal, a log, a CI job's output, a chat transcript, a ticket, a document or a screenshot,
  even if everyone who could see it was trusted
- the secret scan on a repository flagged it ([CHG-0035](/docs/changes/2026/0035-exposed-credentials/))
- a disk or device that held it was lost, stolen, or left Deevnet's hands without being wiped
- a person who knew it no longer has a role that needs it
- a host that held it was compromised, or might have been

Not knowing whether a credential was exposed counts as exposed.

## How soon

**An exposed credential is rotated now if a copy may have left Deevnet, and at the next rebuild if
it did not.** A copy has left Deevnet when it reached a public repository, anyone outside the
operators, an outside service (a chat, a CI provider's logs), lost hardware or a compromised host.
Rotate those at once. A copy that stayed on Deevnet's own systems and in front of its own
operators, such as a value printed to the operator's terminal or a substrate host's log, may wait
for the next rebuild or rotation of what it unlocks. Either way the exposure is recorded, and the
copy is removed where it can be.

## What happens next

**An exposed credential is rotated first and investigated after.** Rewriting history or deleting
the copy is not a fix: copies may already exist elsewhere, so only replacing the credential ends
the exposure.

1. **Rotate it**, with its procedure in the [Credential Rotation](/docs/roadmap/infrastructure/substrate/credential-rotation/plan/)
   plan's list if there is one. Change it on the system that accepts it, then in the vault, then
   on every consumer the list names, and confirm the automation that uses it still works.
2. **Record the rotation as a change** ([Change Management](/docs/policies/change-management/)),
   naming the credential, never its value. Several credentials exposed together get one record, as
   CHG-0035 did.
3. **Write the procedure if it had none.** The rotation just done becomes that credential's
   procedure, in the same change, and the Credential Rotation list says so.
4. **Open an incident** ([Incident Management](/docs/policies/incident-management/)) if the
   credential was used by someone it was not issued to, or if rotating it cost service.
5. **If it cannot be rotated yet**, record it in the
   [risk register](/docs/policies/risk-management/risk-register/) with what it reaches and what
   would let it be rotated. Treat it as exposed until it is.

A credential shared with a tenant is rotated with that tenant: the operator issues the new value,
the tenant takes it up, and the old value is revoked once both sides have moved.
