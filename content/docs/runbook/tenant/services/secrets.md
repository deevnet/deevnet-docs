---
title: "Runtime Secrets"
weight: 9
---

# Runtime secrets

{{< status-badge "active" "Available" >}}

## What you get

**A namespace of your own in the site's OpenBao, `tenants/<name>`, for the secrets your workloads
read while they run**, such as a third-party API key your backend calls with
([ADR-0021](/docs/architecture/decisions/tenant-model/0021-tenant-secrets/)). It is optional: keeping
your secrets encrypted in your repository and pushing them with your settings
([Deploy Your App](/docs/runbook/tenant/deploy-your-app/#your-own-secrets)) still works. Use the
namespace when you want any of these:
- a new value reaching a workload with an apply, with no push and no rebuild;
- one workload cut off at once, without touching the others;
- a record of every read.

**Your repository keeps the real copy.** You write each value through the provider, and it never
reaches your plan or your state. What the namespace holds is always a copy, so if the platform loses
it, your next apply writes it again.

**A workload reads only the paths you give it.** Each workload that needs secrets gets a reader: a
login of its own that can read the paths you name and nothing else. It cannot write, and it cannot
read another tenant's namespace.

## Declare a secret

It needs Terraform 1.11 or later and the `deevnet/deevnet` provider 0.10 or later
(`version = "~> 0.10"`).

```hcl
variable "weather_api_key" {
  type      = string
  sensitive = true
  ephemeral = true   # never stored, not even in a plan file
}

resource "deevnet_secret" "weather" {
  tenant          = deevnet_tenant.this.name
  path            = "backend/weather"
  data_wo         = { api_key = var.weather_api_key }
  data_wo_version = 1
}
```

Decrypt the value from your repository into the variable when you apply, for example
`export TF_VAR_weather_api_key="$(age -d -i ~/.age/key.txt secrets/weather.age)"`.

**`data_wo` is write-only.** Terraform sends it and forgets it, so changing it alone changes
nothing. Raise `data_wo_version` to write a new value. A path is one to four parts of lowercase
letters, digits, `-` and `_`, joined by `/`.

## Give a workload a reader

```hcl
resource "deevnet_secret_reader" "backend" {
  tenant   = deevnet_tenant.this.name
  name     = "backend"
  workload = deevnet_workload.backend.name
  paths    = [deevnet_secret.weather.path]
}
```

It gives back `addr`, `namespace`, `role_id` and `secret_id`. Put them in your workload's settings
and push them with your code, as you push `kit.env`. `secret_id` is the secret half: it is in your
state, like your broker password.

**A reader's login works only from inside the tenant fabric.** It is refused from anywhere else,
your computer included. At this site, it is not tied to the one workload: any workload in the
fabric could use a copy of it. Keep it as you keep the broker password, and delete the reader if it
leaks.

## Read from the workload

**Run your app under OpenBao Agent**, which logs in with the reader, puts each secret in your app's
environment, and restarts the app when a value changes. Nothing is written to the workload's disk
but the reader's two IDs. The reference tenant carries an example: `secrets.tf.example` and
`scripts/run-with-secrets.sh` in `deevnet-tenant-tdemo`. It needs the `bao` command on the
workload.

An app can also call OpenBao itself: log in at `<addr>/v1/auth/approle/login` with the header
`X-Vault-Namespace: <namespace>` and the two IDs, then read `<addr>/v1/secrets/data/<path>` with
the token it gets. The address's certificate chains to the Deevnet Root CA.

## Rotate, revoke, recover

- **Rotate:** a new value in your repository, a higher `data_wo_version`, an apply. A running agent
  picks it up on its next render, within five minutes in the example.
- **Revoke one workload:** destroy its `deevnet_secret_reader`. Its login stops working, and so does
  the token it already holds. An app already running keeps the value it was started with, so stop
  it too, or destroy the workload.
- **After the platform loses OpenBao:** your next apply finds the secrets and readers gone, and
  writes them again. The readers come back with new IDs, so push your settings once more. No
  workload is rebuilt.

## What it does not do

- **No values back.** Nothing in the platform returns a secret to you; your repository is where you
  read it. The API reports only that a path is there and its version
- **Readers bound to the fabric, not the workload.** Tying a reader to its own workload's address
  needs a change to the tenant fabric
- **No other engines.** One key-value store and the readers. No certificates, database credentials
  or other OpenBao engines in your namespace
- **Needs OpenBao to start.** A workload reads its secrets when its app starts. One that is already
  running carries on through an outage; one that starts during it waits
