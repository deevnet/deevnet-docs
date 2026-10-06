---
title: "Deploy Your App to a Workload"
weight: 3
---

# Deploy Your App to a Workload

You develop your app on your computer. This page moves it onto a
[workload](/docs/runbook/tenant/services/network-and-workloads/) in your tenant and keeps it running
there: you build a container image, copy it over SSH, and run it under systemd with one settings
file, `kit.env`. No registry and no operator are involved. The same image and the same `kit.env`
names later carry your app onto [a Pi of your own](/docs/runbook/tenant/tenant-to-pi-image/).

---

## 1. Give the workload your key

A workload trusts exactly the SSH **public** keys you declare in `ssh_keys`, on one account,
`tenant`, which has passwordless sudo. The private key never leaves your computer.

**Started from the [reference tenant](https://github.com/deevnet/deevnet-tenant-tdemo)?** It already
declares the `backend` workload: put your key in `terraform.tfvars` as
`ssh_keys = ["ssh-ed25519 AAAA… you@computer"]` (a list, even of one), and `terraform output backend`
prints the address and the `ssh` line. Its workload is optional, so its address in Terraform is
`deevnet_workload.backend[0]`. Written by hand, the same thing is:

```hcl
resource "deevnet_workload" "backend" {
  tenant   = deevnet_tenant.this.name
  name     = "backend"
  ssh_keys = [file("~/.ssh/id_ed25519.pub")]
}

output "backend_login" {
  value = "ssh ${deevnet_workload.backend.login_user}@${deevnet_workload.backend.fqdn}"
}
```

**Use the key of the computer you develop on,** and check it by fingerprint, not by its comment:
two different keys can carry the same comment. On your computer, compare

```bash
ssh-add -l                                  # the keys your computer offers
ssh-keygen -lf ~/.ssh/id_ed25519.pub        # the key you declared
```

A key is written when the workload is built. To add or change one later, change `ssh_keys` and
replace the workload: `terraform apply -replace=deevnet_workload.backend`
(`-replace='deevnet_workload.backend[0]'` in the reference tenant). A workload boots straight
to ready, so that takes under a minute.

## 2. Log in

From your computer on `DVNTM-TD`:

```bash
terraform output backend        # reference tenant; backend_login if you wrote the block above
ssh tenant@backend.bench1.mobile.deevnet.net 'id; sudo -n true && echo sudo-ok'
```

- **The user is `tenant`,** not your own username. To type only the host name, add to
  `~/.ssh/config`:

  ```
  Host *.bench1.mobile.deevnet.net
      User tenant
  ```

- **A replaced workload has new host keys,** so after you replace one yourself, ssh warns
  `REMOTE HOST IDENTIFICATION HAS CHANGED`. Clear the old entry with
  `ssh-keygen -R backend.bench1.mobile.deevnet.net`, and accept the new key. A warning when you did
  **not** replace the workload is the one to stop at and ask the operator about.
- **`Permission denied (publickey)`** means the connection works and the key does not:
  `ssh -v tenant@… 2>&1 | grep Offering` shows which keys your computer offered. One of them must
  match a key in `ssh_keys`.

## 3. Build your app as a container

Your app reads every setting from its environment, under the names in `kit.env`
([the table](/docs/runbook/tenant/tenant-to-pi-image/#the-one-rule-configure-from-the-environment)),
so the same image runs anywhere. Write `kit.env` from your Terraform outputs, and build the image
for the workload, which is x86-64:

```bash
terraform output -raw kit_env > kit.env               # secret: it holds your broker password and tokens
podman build --platform linux/amd64 -t my-app .
```

`kit_env` is an output of the [reference tenant](https://github.com/deevnet/deevnet-tenant-tdemo),
so a tenant started from it already has one; it names every setting in
[the table](/docs/runbook/tenant/tenant-to-pi-image/#the-one-rule-configure-from-the-environment),
including the backend's own broker login. Run the app once on your computer with the same file
before moving it:
`podman run --rm --env-file kit.env -v ./deevnet-root-ca.pem:/kit/deevnet-root-ca.pem:ro -e MQTT_CA_FILE=/kit/deevnet-root-ca.pem my-app`.

## 4. Copy it to the workload

```bash
H=tenant@backend.bench1.mobile.deevnet.net
podman save my-app | ssh $H sudo podman load            # the image, straight over SSH
ssh $H sudo install -d -m 0755 /opt/my-app
scp kit.env deevnet-root-ca.pem $H:
ssh $H 'sudo install -m 0600 kit.env /opt/my-app/ && sudo install -m 0644 deevnet-root-ca.pem /opt/my-app/ && rm kit.env deevnet-root-ca.pem'
```

The workload has Podman already. `podman load` names the image `localhost/my-app:latest`.

## 5. Run it under systemd

Put this unit on the workload as `/etc/systemd/system/my-app.service`:

```ini
[Unit]
Description=My app (container)
Wants=network-online.target
After=network-online.target

[Service]
Environment=IMAGE=localhost/my-app:latest
ExecStartPre=-/usr/bin/podman rm -f my-app
ExecStart=/usr/bin/podman run --rm --name my-app --network host \
  --env-file /opt/my-app/kit.env \
  -v /opt/my-app/deevnet-root-ca.pem:/kit/deevnet-root-ca.pem:ro -e MQTT_CA_FILE=/kit/deevnet-root-ca.pem \
  ${IMAGE}
ExecStop=/usr/bin/podman stop -t 10 my-app
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
scp my-app.service $H:
ssh $H 'sudo install -m 0644 my-app.service /etc/systemd/system/ && rm my-app.service &&
        sudo systemctl daemon-reload && sudo systemctl enable --now my-app'
ssh $H sudo journalctl -u my-app -f                      # your app's output
```

It starts again by itself after a reboot of the workload.

## Your own secrets

**Secrets you bring yourself live in your repository, encrypted, and travel in the settings file you
push.** A third-party API key, a webhook signing key or a password you chose is yours: the site holds
no copy, so your repository is the only place it survives a rebuild.

- **Keep them encrypted with [age](https://age-encryption.org/)**, to the keys of the computers that
  deploy, and commit the encrypted file:

  ```bash
  age -R recipients.txt -o secrets.env.age secrets.env && rm secrets.env
  ```

- **Merge them into the settings file at deploy time**, next to what the site issued you, and push it
  as in step 4:

  ```bash
  terraform output -raw kit_env > kit.env
  age -d -i ~/.config/age/key.txt secrets.env.age >> kit.env
  ```

- **Rotating one** is a new value in the encrypted file, a push, and a restart.

The file sits on your workload's disk, readable by root only, as `kit.env` does.

## Ship a new version

```bash
podman build --platform linux/amd64 -t my-app .
podman save my-app | ssh $H sudo podman load
ssh $H sudo systemctl restart my-app
```

A changed `kit.env` goes the same way as in step 4, then `systemctl restart`.

## Keep it updated

The workload is yours to maintain: it is built up to date, and after that
`ssh $H sudo dnf upgrade` is on your schedule. Nothing upgrades it behind your back.

## What this does not do

- **A replaced workload comes back empty.** Replacing it (a key change, or a site rebuild) starts
  from the template, so keep these steps in a script beside your Terraform; running it again puts
  your app back. Nothing puts it back for you: a workload holds only what you push to it.
- **No backup.** Data you care about belongs somewhere you declared, not on the workload's disk.
