---
title: "Object Storage"
weight: 10
---

# Object storage

{{< status-badge "active" "Available" >}}

## What you get

**S3-compatible buckets of your own, for your application's data**, with a quota you declare and
keys that reach one bucket each
([ADR-0026](/docs/architecture/decisions/platform-services/0026-object-storage/)). Your buckets
are kept apart from the [state store](/docs/runbook/tenant/services/state-store/), on their own
disk.

- **A bucket is named `<tenant>-<name>`**, at `https://s3.mobile.deevnet.net`, with path-style
  addressing.
- **Each key reaches one bucket.** A key can be read-write (`write`) or read-only (`read`), and it
  is refused every other bucket, yours included.
- **Versioning and expiry are yours to set.** You can keep old versions of each object, and expire
  current objects or old versions after a number of days.
- **A bucket can be readable without a key**, with `public_read`. Anything on the site network
  that can reach the store can then read its objects, such as your devices fetching firmware or
  images. Listing the bucket still needs a key, and nothing outside the site can reach the store.

**The platform stores your objects; it does not back them up.** Keep your own copy of anything
you can't re-derive.

## Declare a bucket

It needs the `deevnet/deevnet` provider 0.11 or later (`version = "~> 0.11"`).

```hcl
resource "deevnet_bucket" "media" {
  tenant      = deevnet_tenant.this.name
  name        = "media"
  quota_gb    = 10
  versioning  = true
  public_read = false

  # Called object_lifecycle because Terraform reserves "lifecycle".
  object_lifecycle {
    noncurrent_expire_days = 30
  }
}
```

**It gives back** the bucket's full name, `bucket`, its `endpoint`, and a read-write key,
`access_key` and `secret_key`. The secret is returned once, when the bucket is made, and is kept
in your state.

**The quota is the most the bucket can hold**, counting every version of every object. The site
allocates quotas and never overcommits them, so a bucket the site has no room for is refused when
you create it. Every argument but `name` changes in place.

**The quota is enforced about a minute behind.** A single-part upload larger than the whole quota
is refused at once. A multipart upload, which is how most clients send a large object, is counted
only after it completes, so one large object can take a bucket past its quota. Past the quota,
writes are refused once the store has counted the bucket, which takes up to about a minute. Treat
the quota as a ceiling to stay under, not a limit to write up to.

## Give a workload its own key

```hcl
resource "deevnet_bucket_key" "reader" {
  tenant = deevnet_tenant.this.name
  bucket = deevnet_bucket.media.name
  name   = "reader"
  access = "read"
}
```

**A `read` key lists and reads, and a `write` key also writes and deletes.** Give each workload or
device the narrowest key it needs, so you can delete one key without touching the others. A key
can't be changed; change any argument and you get a new key with a new secret.

## Use it

**Any S3 client works**, pointed at the endpoint with path-style addressing and the site's root
certificate, `deevnet-root-ca.pem`. For example, with Python and boto3:

```python
import boto3
s3 = boto3.client(
    "s3",
    endpoint_url="https://s3.mobile.deevnet.net",
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    region_name="us-east-1",
    verify="deevnet-root-ca.pem",
    config=boto3.session.Config(s3={"addressing_style": "path"}),
)
s3.upload_file("photo.jpg", "eds-media", "photos/photo.jpg")
```

**Your workloads, your computer on `DVNTM-TD`, and your devices on the IoT network can all reach
the store.** A device reads a `public_read` bucket with a plain HTTPS GET:
`https://s3.mobile.deevnet.net/<tenant>-<name>/<key>`.

## Remove a bucket

**A bucket with anything in it is not deleted.** To empty and delete it, set `force_destroy =
true` and apply first, then remove the resource or destroy it. Everything in it is gone for good,
every version included.
