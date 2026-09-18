---
title: "4. Tenant"
weight: 4
---

# Phase 4: A tenant issues its own key

Merged: `terraform-provider-deevnet` #3.

**No hardware needed.** This phase is where the restore guarantee is proven, and it is proven by
breaking it on purpose.

## Run

In the tenant's own Terraform, for example `/srv/eds/infra/deevnet-tenant-eds`:

```hcl
resource "deevnet_iot_wifi_key" "devices" {
  tenant      = deevnet_tenant.this.name
  name        = "devices"
  trust_class = "iot"
}

output "wifi" {
  value     = {
    ssid = deevnet_iot_wifi_key.devices.ssid
    psk  = deevnet_iot_wifi_key.devices.psk
  }
  sensitive = true
}
```

Build and install the provider, delete the stale lock, then apply:

```bash
cd terraform-provider-deevnet && make build
install -D bin/terraform-provider-deevnet \
  ~/.terraform.d/plugins/registry.terraform.io/deevnet/deevnet/0.1.0/linux_amd64/terraform-provider-deevnet
cd /srv/eds/infra/deevnet-tenant-eds && rm -f .terraform.lock.hcl && terraform init && terraform apply
```

## Verify

1. `terraform output -json wifi` carries `DVNTM-IOT` and a 32-character password.
2. A second `terraform apply` is a **no-op**. If it proposes a change, stop: re-minting the key is
   the one thing that strands devices.
3. **The restore proof.** Delete the key from the controller UI by hand, then:

   ```bash
   terraform plan    # must propose an update, not "no changes"
   terraform apply
   ```

   The key that comes back must be the **identical `psk`**. That is ADR-0012 §5's promise —
   a lost controller costs one apply and never a device visit — and this is the only place it is
   actually tested.
4. The controller shows the key named `eds-devices` on VLAN 30.

## Undo

`terraform destroy -target=deevnet_iot_wifi_key.devices`, or remove the block and apply. Either
revokes the key at the controller.

## The sharp edge

`terraform apply -replace` on this resource, or removing and re-adding the block, issues a **new**
key. Every device flashed with the old one stops associating until it is reflashed. There is
deliberately no guard: revoking is sometimes exactly what is meant. `present = false` restores;
`-replace` does not.
