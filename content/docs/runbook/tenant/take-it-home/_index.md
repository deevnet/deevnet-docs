---
title: "Take Your Tenant Home"
weight: 7
bookCollapseSection: true
aliases: ["/docs/runbook/tenant/tenant-to-pi-image/"]
---

# Take Your Tenant Home

**Your app and the services it uses can move onto hardware of your own, and your devices keep
working with it, with no Deevnet behind them.** The move takes your tenant's backend, the broker,
the log and metrics stores, Grafana, alerting and buckets, onto one machine you own: a Raspberry
Pi, a virtual machine, or a spare computer. It can then go anywhere: home, a classroom, a project
that outlives the site.

```
 on Deevnet                                     on your backend
 ──────────                                     ───────────────
 devices ──TLS 8883──▶ mqtt.mobile.deevnet.net   devices ──TLS 8883──▶ your backend (Mosquitto)
 app     ──TLS 8427──▶ Deevnet log store         app     ──TLS 8427──▶ your backend (VictoriaLogs)
 app     ──TLS 443───▶ Deevnet metrics store     app     ──TLS 8427──▶ your backend (metrics store)
 you     ──TLS 3000──▶ Deevnet Grafana           you     ──TLS 3000──▶ your backend (Grafana)
 phone   ──TLS 443───▶ Deevnet ntfy (on site)    phone   ──TLS 443───▶ your backend (ntfy)
         <tenant>/…  <tenant>/log/<device>               <tenant>/…  <tenant>/log/<device>   ← unchanged
```

**The backend keeps the app contract.** It has the same ports, the same topic prefix, the same
reserved `log` level, the same ingest and read tokens with the same partition header for logs and
metrics, a Grafana organization with the same data source UIDs, and the same alert rules, sent to
the same ntfy topics. What changes is the host name, the CA and the secrets. **Nothing on the
backend belongs to Deevnet.** It has no Deevnet account, key or route, and its CA and tokens are
made on it the first time it boots.

**Every medium carries the same backend.** The same services, the same `deevnet-kit`, which
manages them, and the same self-test, built from one definition. Only how it starts differs.

## The way home

1. **[Prepare your tenant](prepare/)** while it is still on Deevnet: your app reads every endpoint
   from its environment, and Terraform writes that environment for you.
2. **Bring up a backend** on the medium you have. Each page ends with the backend's first boot
   done:

   | Medium | What you get | For |
   |---|---|---|
   | [A Raspberry Pi](raspberry-pi/) | an image you flash to a microSD card | a Pi 3, 4, 5 or Zero 2 W, on Wi-Fi or a cable |
   | [A virtual machine](virtual-machine/) | a disk image for your hypervisor | Proxmox or KVM, VirtualBox, Hyper-V, or UTM on a Mac with Apple Silicon |
   | [A computer of your own](your-own-computer/) | an installer on a USB stick | a spare amd64 computer, on a cable |

3. **[Check the backend](check-the-backend/)**: the self-test, and the files your app needs.
4. **[Move your tenant](move-your-tenant/)**: your broker accounts, your devices, your app, your
   dashboards, alert rules and buckets.
5. **[Choose its certificates](certificates/)**, if you want more than the backend's own CA: one
   from Deevnet for your tenant's names, or a PKI of your own when you leave.

Your Deevnet tenant is untouched by any of this. Destroy it with `terraform destroy` when you are
done, or keep prototyping there. The two do not share a secret.

## What does not come along

| On Deevnet | On your backend |
|---|---|
| Workload VMs | Your app runs on the backend or your computer |
| `<tenant>.mobile.deevnet.net` DNS | `<hostname>.local`, and the backend's address for devices |
| Wi-Fi keys on `DVNTM-IOT` | Your own Wi-Fi |
| The device registry | Device names are checked for shape only |
| Terraform state and the API token | Nothing to apply: `deevnet-kit` is the whole control plane. Only your dashboards are still Terraform, against the backend's Grafana |
| Your metrics and logs so far | The backend starts empty; Deevnet keeps yours until the tenant is removed |
| Alert rules from the API | Exported from your Terraform and imported ([Move your tenant](move-your-tenant/#your-alert-rules)) |
| Alerts away from the site | Alerts on the backend's network only, for now |
| Your buckets' objects | You copy them ([Move your tenant](move-your-tenant/#your-buckets)) |
| Runtime secrets | Not on the backend: put what your app needs in its own environment, beside `kit.env` |

## Where it differs, for the careful

- **The broker is Mosquitto**, not VerneMQ. The wire protocol, ports and topic rules are the same.
- **A subscription outside your grant** is refused in the SUBACK on Deevnet. On the backend it is
  accepted and nothing is delivered. Either way no message crosses.
- **Revocation** is immediate on the backend and takes effect on the next connect on Deevnet.
- **You are Grafana's admin on the backend** (`grafana_admin_password` in
  `/etc/deevnet-kit/kit.json`). Your tenant login is still an Editor, so the same Terraform runs on
  both.
- **Metrics are kept 30 days**, not 90: a backend is not a data disk.
- **An alert's "Source" link** points at the backend's vmalert on an internal port, which the phone
  can't open. The message itself carries the alert's name, status and summary.

The images are built in `deevnet-image-factory`: `make pi-backend` for the Pi
(`docs/pi-backend.md`), `make vm-backend` and `vm-backend-arm64` for the virtual machine,
`make vm-formats` for VirtualBox and Hyper-V, and `make iso-backend` for the installer.
`deevnet-kit` lives in `deevnet-provisioning-api` beside the rules it applies.
