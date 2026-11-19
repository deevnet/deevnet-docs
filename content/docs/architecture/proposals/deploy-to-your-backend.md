---
title: "Deploy to Your Backend"
---

# Proposal: One Way to Deploy a Tenant's Services to Its Backend

| | |
|---|---|
| **Status** | Proposal, not decided and not built |
| **Date** | 2026-11-19 |
| **Where** | `tenant2backend`, in `deevnet-provisioning-api`: on the take-home backend, and on the owner's computer |
| **Would extend** | [Take Your Tenant Home](/docs/runbook/tenant/take-it-home/), [ADR-0044](/docs/architecture/decisions/tenant-model/0044-take-home-media/), [ADR-0045](/docs/architecture/decisions/tenant-model/0045-take-home-tool-owners-name/); in EdS, its ADR-0015 and ADR-0033 |

A tenant with several services of its own, such as EdS, deploys every new build to its take-home
backend the same way a tenant with one app does, on every medium. Each service carries a short
manifest; `tenant2backend deploy`, run from the owner's computer on any operating system, sends what
changed; and `tenant2backend service` on the backend builds it, makes its broker login and
settings, and runs it. The stock image of each medium is all any tenant flashes. Its customer is
every tenant owner, and first EdS's.

## Why

**Today a tenant's code reaches its backend in two different ways.** The guide's way is one app:
a container built on the owner's computer, copied with `podman save | ssh … podman load`, given its
settings by `tenant2backend export` and run by an example unit. It does not say how a tenant with
several services, settings and secrets does it.

**EdS does it by building its own image.** Its backend image is the stock Pi image with EdS's
layer applied offline on the Builder (EdS ADR-0015, ADR-0033): four services and the agent run
natively, and `eds-backend-setup` makes their broker accounts on the card. Every new build of any
service means a new image and a reflashed card, or EdS's own push. The same services run on EdS's
Deevnet workload as containers, so each runs two ways. And the image exists only for the Pi: EdS
cannot try its backend on the virtual machine on a Mac without a second image of its own.

**ADR-0033 chose native for two reasons, and one goes away.** Podman cannot load an image into a
card that is not running, but a deploy to a backend that is running has no such limit. The other,
memory on a Pi that also runs Grafana, is a sizing question to measure.

## What it is

- **Each service is described by a manifest in the tenant's repository.** It names the service,
  how it is built (a container, from its sources), the broker account it needs and that account's
  grants, its settings file, any secret files the owner supplies, and the devices it needs, such as
  a sound card.
- **The owner runs one command to deploy, from Mac, Windows or Linux.** `tenant2backend deploy
  you@backend DIR` is the same tool the backend runs, built for the owner's computer as the
  provider is. It sends over SSH only what changed since the last deploy, then calls the backend's
  side.
- **The backend builds the service itself.** `tenant2backend service` runs `podman build` on the
  backend, so the image is always the backend's architecture and the owner's computer needs no
  container tool. EdS's scribe already builds on its workload this way.
- **The backend makes each service's login and settings.** From the manifest, `tenant2backend`
  makes the service's broker account with its grants and keeps its password across deploys, as
  `eds-backend-setup` does today, writes the service's `kit.env`, installs the owner's secret
  files where only that service reads them, and writes its unit.
- **`tenant2backend service list|restart|rm` look after what is deployed.** The status and the
  self-test include the tenant's services.
- **Every tenant flashes the stock image.** Nothing of a tenant's goes into an image; EdS stops
  building its own once the process covers what its Pi needs.

## What it is not

- **Not a way to bake a tenant's services into an image.** Deploying happens after first boot, on a
  running backend.
- **Not a registry or a remote builder.** Sources go over SSH to the backend, which builds.
- **Not for Deevnet's workloads yet.** EdS's `deploy/` stays how EdS reaches its Deevnet workload;
  the same manifest reaching a workload is Later.
- **Not a secret store.** The owner supplies a service's secrets at deploy time, from wherever the
  tenant keeps them (EdS: its sops files); the backend keeps them on its own disk only.
- **Not a change to the app contract.** A service reads the same `kit.env` names it reads on
  Deevnet.

## The MVP

**EdS's six workload services, deployed onto the stock arm64 virtual machine in UTM on the owner's
Mac, by `tenant2backend deploy`, with a manifest each.** Containers only: the backend builds each,
makes its broker account and settings from its manifest, and runs it; a second deploy after a
change sends only that service and restarts only it. On the first day the owner runs EdS's console
and lights from the VM on the Mac, changes one service, and deploys it with the same command.

## Versions

- **v1, the MVP:** containers; the manifest (build, broker account, settings, secrets); `deploy`
  from any operating system and `service` on the backend; EdS's six services on the stock UTM
  virtual machine.
- **v2:** native services and device access in the manifest; EdS's agent (`npagent`, the sound card
  and its iTunes pairing) by the same process; EdS's production Pi built from the stock Pi image
  and deployed to, and EdS stops building its own image.
- **Later:** the same manifest and `deploy` for a Deevnet workload, so EdS's `deploy/` can retire;
  rolling back to the previous build of a service; deploying from CI; a tenant template (in
  `deevnet-tenant-tdemo`) with a manifest to copy.

## Open questions

- **The manifest's format and name**, and what is required in it: settled in v1's ADR (Deevnet).
- **Memory on a Pi:** EdS's services as containers beside Grafana and the stores. Measured on the
  production Pi in v2, which decides which Pi it needs.
- **Building on a Pi:** how long `podman build` takes there, and the disk it needs. Measured in v2;
  the virtual machine in v1 says how long on a Mac.
- **The native form for v2**: a binary and its unit, or a Debian package. Decided when v2 is cut.
- **EdS's records:** EdS ADR-0015 and ADR-0033 are superseded in part by an EdS ADR, written in
  EdS when v2 is cut.
- **Backends flashed before the process exists** have no `deploy` side: they are reflashed from a
  newer image, as with every change to the tool.
