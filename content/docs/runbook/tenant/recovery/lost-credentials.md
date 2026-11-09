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

**Your state-store keys live inside the state they unlock, so without a copy the operator gives you a
new secret key.**

- **The access key is your tenant name.**
- **The secret key you had can't be recovered from the site.** Nothing hands it back.
- **Ask the operator for a new one.** You receive the two lines of your `.backend.env`. Put them in
  place of the old ones on every computer that reads your state, and in CI if you use it: the old
  key stops working.

**Don't restore your tenant from the state you had before.** It still holds the old key, and a
restore would put that key back and lock you out again.

## Keep it from happening

- Keep your state in the site's state store, or somewhere you back up
  ([State store](/docs/runbook/tenant/services/state-store/)).
- Keep `terraform.tfstate.backup` from the move somewhere safe, not in the repository. It holds
  secrets.
- Never commit state. It holds every secret your tenant has.
