---
title: "Segment Check"
weight: 5
---

# Segment Check

Checking from a real client that each Wi-Fi segment reaches what the zone policy allows and nothing
else.

The firewall role reports what it **wrote**. It cannot report what a client **gets**: whether a lease
lands in the right subnet, whether names resolve through the segment's own gateway, or whether a
denied port is really dropped. The only place to see that is a laptop on the SSID.
`scripts/segment-check.sh` in
[`ansible-collection-deevnet.net`](https://github.com/deevnet/ansible-collection-deevnet.net/blob/main/scripts/segment-check.sh)
does it in one run per SSID.

## When to run it

- After any change to `firewall.yml`, `vlans.yml` or the router's DNS or DHCP. Run it for every
  SSID the change touches, as the change record's verification
  ([CHG-0022](/docs/changes/2026/0022-tenant-dev-network/),
  [CHG-0023](/docs/changes/2026/0023-internet-means-internet/)).
- When a tenant says they can't reach the API or the broker. Have them run the `DVNTM-TD` profile
  and send you the output.
- Any time you want to confirm the policy still holds, e.g. after a router upgrade or restore.

## Running it

It needs only what macOS already has (`bash`, `nc`, `dig`, `curl`, `openssl`). The site CA is built
in. Linux works where `timeout` and `dig` are installed.

```bash
curl -fsSLO https://raw.githubusercontent.com/deevnet/ansible-collection-deevnet.net/main/scripts/segment-check.sh
bash segment-check.sh --list          # what each SSID checks
bash segment-check.sh DVNTM-TD        # join the SSID first, then name it
```

1. Join the SSID. Turn off any VPN, iCloud Private Relay or fixed DNS server: the script checks that
   names are answered by the segment's own gateway, and they will fail if something else answers.
2. Run it with that SSID's name. If the laptop's address isn't in that SSID's subnet, the script
   stops at the first check, so running the wrong profile can't produce a misleading pass.
3. Exit status is 0 only if every check passed.

## Reading the result

| Line | Passes when | Why |
|---|---|---|
| `REACH` | the connection opens **or is refused** | either way the router let the packet through to the host |
| `BLOCK` | the connection **times out** | the router silently drops what policy denies, so a refusal means the packet reached the host. It is reported as a **LEAK** |
| `REACH provisioning API` | HTTPS answers with any status, TLS verified against the site CA | reachable and correctly signed. `404` on `/` is normal |
| `tls` | the handshake verifies against the site CA | the broker is TLS only |
| `resolve` | the name resolves **through the segment's gateway** | answered by anything else means a VPN or fixed DNS on the laptop, not the site |

**Hosts that are switched off.** A REACH against a host that is off fails, and a BLOCK against one
**passes whatever the policy says**, because a dead host times out too. The IoT Pis are often off,
so their lines are labelled: `fails-if-off` on REACH from trusted, and `if-on` on BLOCK elsewhere,
meaning that pass proves nothing unless the Pi is running. The broker host is always on and is the
dependable check on the IoT side.

## What each SSID should get

| SSID | Segment | Reaches | Must be blocked from |
|---|---|---|---|
| `DVNTM` | trusted | management (lab exception), the provisioning API, state store, broker, Pis, tenant workloads, the edge router, the internet | the router on iot_vendor, guest and tenant_dev |
| `DVNTM-TD` | tenant_dev | the provisioning API `:8080`, state store `:9000`, broker `:8883`, the internet | management, the router's own address, other ports on those hosts, iot, tenant workloads, the edge router |
| `DVNTM-IOT` | iot | the broker `:8883`, the internet | management, the router's own address, the API and state store, tenant workloads, trusted, the edge router |
| `DVNTM-IOTV` | iot_vendor | the internet | everything internal, including the broker, and the edge router |
| `DVNTM-GUEST` | guest | the internet | everything internal, and the edge router |

`--list` prints the exact hosts and ports. `DVNTM-IOT` needs a laptop joined with a tenant's PPSK
key, since that SSID has no shared key.

## When a check fails

| Failure | Look at | Fix with |
|---|---|---|
| lease in the wrong subnet, or none | the SSID's VLAN on the AP trunk, the Kea subnet | `make switch`, `make dhcp`, `make wireless` |
| `resolve` answered by another server | the laptop first (VPN, Private Relay, fixed DNS), then Kea's DNS option | the laptop's settings, or `make dhcp` |
| REACH times out | the zone policy: is the flow declared? Then the target: is it on? | `firewall.yml`, then `make migration-opnsense-firewall` (plan, then `EXTRA_ARGS="-e firewall_apply=true"`) |
| BLOCK is a **LEAK** | a zone-level pass wider than intended, or an internet rule reaching private space | `firewall.yml` and the internet rule (`firewall_internet_private_zones`), same apply |
| TLS fails to verify | the service's certificate, or an old CA on the laptop | the service's role; the embedded CA is the site CA |

Take a leak seriously even on a segment that "shouldn't matter": it is the router letting a packet
through that the policy says it drops.

## Keeping it true

The profiles are a hand-kept copy of the mobile zone policy (`firewall.yml`,
`firewall_internet_zones`, `firewall_internet_private_zones`) and of `vlans.yml`. They are copied so
the script runs on a bare laptop. **Change them in the same PR as the policy.** A profile that lags
the policy either fails a correct change or, worse, never checks the new flow.

Targets should be hosts that are always on. The broker, the provisioning host, the Builder, the
router, the hypervisor and eds's workload are. The Pis are not, and are labelled accordingly.
