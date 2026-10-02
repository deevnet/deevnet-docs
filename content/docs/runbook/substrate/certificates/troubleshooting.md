---
title: "Troubleshooting"
weight: 7
---

# Troubleshooting

Set `R=/srv/dvnt/ansible-inventory-deevnet/pki/mobile/deevnet-mobile-root-ca.pem` first.

## Is it the site's certificate, and does it chain?

```bash
openssl s_client -connect <host>:<port> -servername <name> -showcerts -CAfile $R </dev/null 2>&1 \
  | grep -E '^ *[0-9] s:|Verify return code'
```

- **One certificate, no intermediate:** the service is sending its leaf alone. Clients that hold only
  the root cannot build the chain.
- **`unable to get local issuer certificate`:** a certificate from something other than the site
  root. It is either the device's own, or one issued before a re-root. Re-run its role or
  `certs.yml`; `site_cert` and `proxmox_node_cert` reissue anything that does not chain.
- **`Verify return code: 0` but the client still refuses:** check the name. Add
  `-verify_hostname <name>`, or `-verify_ip <address>`, for exactly what the client dials. Every name
  and address comes from the inventory (`site_cert_dns_names`, `site_cert_ip_sans`); a CNAME missing
  from `env.interfaces.<if>.dns.cnames` is a name the certificate does not carry.

```bash
openssl x509 -noout -ext subjectAltName <<<"$(openssl s_client -connect <host>:<port> </dev/null 2>/dev/null)"
```

## A container service resets every handshake

The listener is up and the service reports it running, yet `openssl s_client` gets
`errno=104` (connection reset). The service cannot read one of its own files, usually the root.

A directory a container mounts with `:Z` carries that container's private SELinux label, and podman
applies it only when it **creates** the container. A file written there afterwards, such as a new
root file, gets the host's default label, and a container that is only restarted cannot read it.

```bash
sudo ls -Z /srv/<service>/tls/     # every file should match the directory's label
```

`site_cert` gives its files their directory's label on every run, and the broker's role waits for a
verified handshake rather than trusting the listener's state. By hand:
`sudo chcon --reference=<dir> <file>`, then restart the service. This happened to the broker during
[CHG-0031](/docs/changes/2026/0031-site-root-ca/).

## A client still skips verification

The appliances' clients verify only when the inventory's switch is on: `site_verify_proxmox`,
`site_verify_opnsense`, `site_verify_omada`. The Deevnet API takes them from its container
environment:

```bash
ssh a_autoprov@dv02prv001v01.mobile.deevnet.net \
  "sudo podman inspect deevnet-api --format '{{range .Config.Env}}{{println .}}{{end}}'" \
  | grep -E 'INSECURE_TLS|SSL_CERT_FILE'
```

A changed switch reaches the API on its next deploy (`site.yml --limit dv02prv001v01 --tags deevnet-api`).

## A tool on the Builder does not trust the root

The Builder trusts the root at the OS level: `trust list --filter=ca-anchors | grep Deevnet`. Ansible,
Packer and Terraform verify through that. A Python tool that bundles its own CA list (`certifi`)
would not; the Builder's Ansible runs on the system Python, which uses the OS bundle.
