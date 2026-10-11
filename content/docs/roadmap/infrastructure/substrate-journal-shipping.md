---
title: "Substrate Journal Shipping"
weight: 9
tasks_completed: 0
tasks_in_progress: 0
tasks_planned: 3
---

# Substrate Journal Shipping

Substrate hosts keep their journals to themselves. Reading across the site is an SSH session per
host. [ADR-0022](/docs/architecture/decisions/platform-services/0022-central-logging/) describes
shipping them to the log store with `systemd-journal-upload`; the store was then narrowed to
tenants' logs ([ADR-0027](/docs/architecture/decisions/platform-services/0027-tenant-log-store/)),
and the shipping was never deployed.

**To be considered, not scheduled.** The substrate exists to run tenants, and this is work on the
substrate for its own sake. It is written down so that what was learned is not lost, and so it can
be weighed against tenant work when someone next wants a host's logs and has to go and fetch them.

{{< overall-progress >}}

**Legend:** ✅ Complete | 🔄 In Progress | ⏳ Planned

---

## Project Vision & Scope

An operator reads any substrate host's journal from one place, and a host that has gone down has
already sent what it had to say.

**In Scope**
- Fedora substrate hosts shipping their own journal, store and forward, each with its own token
- Where substrate logs live now that the log store is the tenants'

**Out of Scope**
- The Builder, which roams and ships nowhere
- Hypervisors and network devices, which ADR-0022 sends by syslog
- Tenant workloads, whose shipping is the tenant's choice

---

## What was tried

A `journal_upload` role was written and run against one host, `dv02nms001v01`, on 2026-09-21. It
delivered 194 thousand lines, and was then reverted there. The role was never merged; its branch
was discarded on 2026-10-11 and this page is what remains of it. It was about 200 lines and would
be quicker to write again than to revive.

Three things the trial found, each of which stops it working and none of which is obvious:

- **SELinux.** The store's port must be labelled `journal_remote_port_t`, or
  `systemd_journal_upload_t` cannot connect to it.
- **No client certificate.** `ServerKeyFile=-` and `ServerCertificateFile=-` must be set, or
  journal-upload demands a client certificate it does not have.
- **The token's file mode.** The token is a `Header=` line in a drop-in. The Fedora unit runs as a
  dynamic user, so a root-only file stops the service reading its own configuration, and the stock
  mode hands the token to every local user. The drop-in is `0640 root:systemd-journal`.
  journal-upload cannot read `Header=` from a systemd credential.

`Header=` needs systemd 258 or later; Fedora 44 has 259. The local journal stays the first copy,
and the unit resumes from saved state after an outage.

---

## Before it could go in ⏳

- ⏳ **The first run sends the whole journal.** A host that has been up for months sends months.
  Decide whether to start from now, or to let the backfill run and at what cost to the store.
- ⏳ **NIC stability on the core router.** The trial raised a doubt about shipping from it under
  load. Settle it on that host before it ships anything.
- ⏳ **Where substrate logs go.** ADR-0027 made the log store the tenants'. Substrate logs need a
  decision of their own: a partition there that no tenant can read, or somewhere else.
