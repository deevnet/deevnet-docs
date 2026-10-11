---
title: "Service Certificates"
weight: 8
---

# Service certificates {{< status-badge "active" "Available" >}}

## What you get

A server certificate for a service you run on a workload, for a name in your own zone, such as
`console.<name>.mobile.deevnet.net`. It is signed by the site's Tenant Service CA and chains to the
**Deevnet Root CA**, which every computer on the site that reaches your service already trusts. A
browser opens your page with no warning and nothing extra to install
([ADR-0037](/docs/architecture/decisions/substrate/0037-tenant-service-certificates/)).

**You make the key and you keep it.** Only a signing request goes to the platform. The key is in
your Terraform state and on your workload, and nowhere else.

## Declare a certificate

It needs the `hashicorp/tls` provider beside `deevnet/deevnet`, for the key and the request.

```hcl
resource "tls_private_key" "console" {
  algorithm   = "ECDSA"
  ecdsa_curve = "P256"
}

resource "tls_cert_request" "console" {
  private_key_pem = tls_private_key.console.private_key_pem

  subject {
    common_name = "console"   # a label for your own reading; it is not used
  }
}

resource "deevnet_certificate" "console" {
  tenant  = deevnet_tenant.this.name
  name    = "console"         # -> console.<name>.mobile.deevnet.net
  names   = ["www"]           # optional: more labels in your zone
  csr_pem = tls_cert_request.console.cert_request_pem
}
```

**You write labels, not names.** The platform appends your zone, as it does for a
[DNS record](/docs/runbook/tenant/services/dns/). A label with a dot, a wildcard or an address is
refused.

**What your request says about itself is not used.** The certificate's subject, names and lifetime
are the platform's, the same for every tenant. Only the key in the request is yours.

Publish the name as well: a certificate does not create a DNS record.

## Serve with it

| Attribute | What it is |
|---|---|
| `tls_private_key.console.private_key_pem` | your key; sensitive |
| `deevnet_certificate.console.fullchain_pem` | the certificate, then the two CAs a server presents after it |
| `deevnet_certificate.console.certificate_pem`, `ca_chain_pem` | the same, apart |
| `not_after`, `renew_after` | when it expires, and when a plan starts to renew it |

Most servers want two files: the key, and `fullchain_pem`. Put both on your workload the way you
put your settings there ([Deploy Your App](/docs/runbook/tenant/deploy-your-app/)), readable only
by the account your service runs as.

**Do not send the root.** `fullchain_pem` holds your certificate, the Tenant Service CA and the
Site CA. The client already holds the root and builds the chain from those.

## Renew it

**A certificate lasts one year, and renewing it is an apply.** From sixty days before it expires,
`terraform plan` shows `deevnet_certificate` changing. Apply, and put the new certificate on your
workload. The key stays the same unless you replace it.

**Nothing renews it for you.** A tenant that applies nothing for a year serves an expired
certificate, and every browser refuses it. Run a plan at least every ten months.

## What it does not do

- **Your zone only.** A certificate is for names under `<name>.mobile.deevnet.net`. You cannot ask
  for another tenant's name or a platform name, and there is no field to ask with
- **No wildcards and no addresses.** One certificate holds up to eight names, each a single label
- **No revocation.** Destroying the resource, or replacing the key, does not withdraw the old
  certificate. It stays valid until it expires, wherever its key still is. Guard the key
- **No renewal on a clock.** See above
- **Not for devices.** A device proves who it is with a client certificate from another CA
  ([Devices & MQTT](/docs/runbook/tenant/services/devices-and-mqtt/)); this is for servers
- **Trusted on the site, not on the internet.** The Deevnet Root CA is private. A computer that has
  not been given it will not trust your service
