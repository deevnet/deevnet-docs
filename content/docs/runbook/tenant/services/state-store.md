---
title: "State Store"
weight: 7
---

# State Store {{< status-badge "active" "Available" >}}

## What you get

An S3-compatible place for your Terraform state, with a key prefix only your credentials can reach
([ADR-0007](/docs/architecture/decisions/0007-terraform-state-custody/)). It is **offered, not
required** — keeping state yourself is a valid choice, as long as you keep it carefully: it holds
every credential your tenant was issued.

## Move your state into it

The credentials are attributes of your tenant, so this happens after the first apply:

```hcl
terraform {
  backend "s3" {
    bucket       = "tf-state"
    key          = "tenants/bench1/terraform.tfstate"    # state_key_prefix + terraform.tfstate
    region       = "us-east-1"
    endpoints    = { s3 = "http://tfstate.mobile.deevnet.net:9000" }
    use_lockfile = true

    # S3-compatible, not AWS.
    skip_credentials_validation = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    skip_s3_checksum            = true
    use_path_style              = true
  }
}
```

Add an output for the credentials, then read them:

```hcl
output "state_backend" {
  sensitive = true
  value = {
    endpoint   = deevnet_tenant.this.state_endpoint
    bucket     = deevnet_tenant.this.state_bucket
    key        = "${deevnet_tenant.this.state_key_prefix}terraform.tfstate"
    access_key = deevnet_tenant.this.state_access_key
    secret_key = deevnet_tenant.this.state_secret_key
  }
}
```

```bash
terraform apply                                  # to record the new output
terraform output -json state_backend             # the values for the block above
export AWS_ACCESS_KEY_ID=<access_key>
export AWS_SECRET_ACCESS_KEY=<secret_key>
terraform init -migrate-state
```

The reference tenant's `make state-backend` prints the block and both keys for you.

## What it does not do yet

- **It is plain HTTP today**, inside the site. Your state crosses the platform network
  unencrypted in transit; the design says TLS
  ([ADR-0026](/docs/architecture/decisions/0026-object-storage/))
- **It has no second copy.** The store lives on one disk
  ([ADR-0014](/docs/architecture/decisions/0014-tenant-state-durability/), Proposed). Keep a copy
  of anything you cannot re-issue
- It is for state, not application data. Buckets for your workloads are
  [coming](/docs/runbook/tenant/services/coming-soon/#object-storage)
