---
title: "Lost State or Credentials"
weight: 2
---

# Lost State or Credentials

Your Terraform state holds every credential your tenant was issued, and for your **API token** it is
the only copy. What you can get back depends on what you still have.

| You still have | You lost | Do this |
|---|---|---|
| Your state | Your API token in this shell | `export DEEVNET_API_TOKEN=$(terraform output -raw api_token)` |
| State in the site's state store | The keys to read it (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) | See [below](#keys-to-the-state-store) |
| A local `terraform.tfstate.backup` from before you moved state into the store | Everything else | That file holds your API token and the state-store keys from before the move. Read them out without printing them, then read your state as usual |
| Nothing | Your state and your token | Your tenant cannot be reached through its own Terraform. Ask the operator; the recovery is a rebuild, and devices need their keys reissued and reflashing |

## Keys to the state store

**Your state-store keys live inside the state they unlock, and there is no way yet to get the secret
key back without them.**

- **The access key is your tenant name.**
- **The secret key can't be recovered from the site today.** A reconcile deliberately doesn't return
  it, and there is no reissue yet. An operator reissue of the state secret is planned
  ([2026-10 review, T2](/docs/architecture/reviews/2026-10-rebuild-and-access/#t2-state-key-recovery)).

Until then, the only way back is a copy you kept: `.backend.env`, or the
`terraform.tfstate.backup` from before the move. Without one, ask the operator; the recovery is the
same as having lost everything, in the last row above.

## Keep it from happening

- Keep your state in the site's state store, or somewhere you back up
  ([State store](/docs/runbook/tenant/services/state-store/)).
- Keep `terraform.tfstate.backup` from the move somewhere safe, not in the repository. It holds
  secrets.
- Never commit state. It holds every secret your tenant has.
