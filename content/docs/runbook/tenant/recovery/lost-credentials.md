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

Your state-store keys live inside the state they unlock. You can get back in without them:

- **The access key is your tenant name.**
- **The secret key** is one of the secrets the site keeps for you. Ask the operator to reconcile your
  tenant ([Tenant Admission → Operator-only calls](/docs/runbook/substrate/tenant-admission/#operator-only-calls)).
  The reconcile response carries your state secret, which the operator hands to you like an
  enrollment token.

With both exported, `terraform init` reads your state again, and `terraform output -raw api_token`
gives back your API token. This path follows from how the API behaves, and has not been exercised
end to end.

## Keep it from happening

- Keep your state in the site's state store, or somewhere you back up
  ([State store](/docs/runbook/tenant/services/state-store/)).
- Keep `terraform.tfstate.backup` from the move somewhere safe, not in the repository. It holds
  secrets.
- Never commit state. It holds every secret your tenant has.
