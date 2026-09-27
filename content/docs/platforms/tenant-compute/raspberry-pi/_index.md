---
title: "Raspberry Pi"
aliases:
  - /docs/platforms/tenant-compute/raspberry-pi-lab/
weight: 2
bookCollapseSection: true
---

# Raspberry Pi

Fills the **Pi lab** role — bare-metal hosts lent to tenant projects that need a Pi rather than a
VM. See [Substrate Compute → The Pi lab](/docs/architecture/substrate/compute/#the-pi-lab).

The SD card is the unit that moves: a project is developed on a lab Pi, and when it works the card
goes into a Pi the project owns, and the lab Pi takes the next card.

---

## Hardware

[Raspberry Pi 4 Model B](/docs/platforms/hardware/compute/raspberry-pi-4/): four units: specs, switch ports and console.

---

## Network Position

Lab Pis sit on the IoT segment. Their hostnames and switch ports are in the
[Network Reference](/docs/runbook/substrate/network/network-reference/) and the
[Raspberry Pi 4](/docs/platforms/hardware/compute/raspberry-pi-4/) hardware page.

---

## Operating System

| Attribute | Value |
|-----------|-------|
| **OS** | Raspberry Pi OS (64-bit) or Fedora ARM |
| **Provisioning** | SD card imaging via deevnet-image-factory |

---

## Use

How the bank is used — building an image, testing on a bank Pi, and graduating a project to
dedicated hardware — is the [Pi Lab](/docs/runbook/tenant/pi-lab/) in Tenant Operations. Projects
that have graduated are under [Completed Projects](/docs/completed/).
