---
title: "CHG-0045: A Service Name for Grafana"
weight: -45
---

# CHG-0045: A Service Name for Grafana

| | |
|---|---|
| **Date** | 2026-10-10 |
| **Change type** | Configuration |
| **Classification** | Structural |
| **Status** | Complete, except that tenants other than `mabell` have not been told. See [Outcome](#outcome) |
| **Window** | 2026-10-10 05:29 to 05:34 EDT (steps 1 to 4); step 5's guide change the same day |
| **Site** | mobile |
| **Systems** | `dv02obs001v01` (Grafana), `dv02cor002p01` (the site resolver), `dv02prv001v01` (the Deevnet API) |
| **Automation** | `deevnet.net` `dns.yml`; `deevnet.mgmt` `site_cert`, `grafana` and `deevnet_api` roles, `site.yml --tags dashboards` and `--limit deevnet_api`; the `mobile` inventory |
| **Risk** | Low. Most likely to go wrong: the API handing tenants the new name before Grafana's certificate carries it, which fails every tenant's dashboard apply. The step order guards it |
| **Related changes** | [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/) (the dashboards this names), [CHG-0025](/docs/changes/2026/0025-tenant-downloads/) (`downloads`, the same pattern on the same host), [CHG-0033](/docs/changes/2026/0033-deevnet-pki/) (the CA that signs the certificate) |
| **Related incidents** | None |
| **Related runbooks** | [Dashboards](/docs/runbook/tenant/services/dashboards/), [DNS](/docs/runbook/tenant/services/dns/) |

---

## Summary

Tenants reach their dashboards at a host name, `dv02obs001v01.mobile.deevnet.net:3000`. The broker
is `mqtt`, the API is `api`, the downloads site is `downloads`; Grafana alone is named for the
machine it happens to run on, and every tenant's bookmark and Terraform state would change if it
moved.

This change gives it a service name, `grafana.mobile.deevnet.net`, owned by the substrate like the
others: an alias in the substrate's zone, on Grafana's certificate, and the address the API hands
every tenant.

### What was tried first

On 2026-10-09 the `mabell` tenant published `grafana.mabell.mobile.deevnet.net` in its own zone, as
a CNAME to the host, by a signed update with its TSIG key. It resolved, and it showed why the name
belongs to the substrate and not to each tenant:

- The certificate would need a name per tenant, reissued at every admission, from a tenant list the
  inventory deliberately does not hold. A wildcard would not cover a name one label deeper.
- One certificate naming every tenant shows each tenant the others.
- The site resolver answered the CNAME with `NXDOMAIN` for its target, though it resolves the target
  when asked directly.

Grafana is a substrate service, so the substrate names it. The tenant's record is withdrawn; see
[Follow-ups](#follow-ups) for the resolver behaviour, which this change no longer depends on.

## Goal

- `grafana.mobile.deevnet.net` resolves to Grafana's address through the site resolver, with
  `NOERROR`, from an operator network and from `DVNTM-TD`.
- Grafana's certificate carries `grafana.mobile.deevnet.net`, the host's own name and its address.
- `site_cert` reissues a certificate when a name it is asked for is missing from the one installed.
- `curl --cacert <root> https://grafana.mobile.deevnet.net:3000/api/health` returns `200` with
  verification on, and so does the same request by host name.
- Grafana's root URL is the service name.
- A tenant's `dashboard_url` is `https://grafana.mobile.deevnet.net:3000`, and a tenant's Terraform
  applies its dashboards through it with a second apply planning nothing.

## Scope

**In scope:** the alias in inventory; the name on Grafana's certificate; the `site_cert` reissue
rule; Grafana's domain and root URL; the address the API hands out; the tenant guide.

**Out of scope:**
- the port, which stays `3000` ([CHG-0024](/docs/changes/2026/0024-tenant-dashboards/) explains why)
- a firewall rule: none changes, since the name leads to the address already admitted
- names for the log store and the state store on the same pattern
- any name in a tenant's zone

## Risk and impact

| Risk | Where | Guard |
|---|---|---|
| The API hands out the new name before the certificate carries it | every tenant's Terraform | Order: step 3 before step 4. The Grafana provider verifies the certificate |
| The new reissue rule reissues other services' certificates | every host that uses `site_cert` | The rule fires only when a wanted name is missing. The check run in step 1 must report Grafana's certificate and no other |
| The reissued certificate lacks the host's name | Grafana, and the API's own calls to it | The host's name stays on the certificate as an alternative name, as `downloads` keeps its host's. Step 3 checks both names before step 4 |
| A tenant's bookmark or state holds the old address | tenants | The host name keeps working with a valid certificate. `dashboard_url` is read from the API on every plan |
| Grafana redirects a visitor at the host name to the service name | operators, tenants | Expected once the root URL changes, and harmless: both names are on the certificate |
| Grafana restarts | tenants' browsers | A few seconds. Sessions survive: they are in Grafana's database |

## Prerequisites

- [x] Pull requests merged: the inventory (`grafana` added to `dv02obs001v01`'s `cnames`),
  `deevnet.mgmt` (`site_cert`, `grafana`, `deevnet_api` defaults)
- [x] Vault decrypted, collections built
- [ ] Tenants told the address is changing and that the old one keeps working. Only `mabell` was

## Procedure

### Step 1: Read what is there

Read-only.

**Run:**

```bash
dig @10.20.10.1 grafana.mobile.deevnet.net

openssl s_client -connect dv02obs001v01.mobile.deevnet.net:3000 </dev/null 2>/dev/null \
  | openssl x509 -noout -ext subjectAltName

cd ansible-collection-deevnet.net
ansible-playbook playbooks/dns.yml --check
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --check
```

**Verify:**

1. The name does not resolve.
2. The certificate names the host and its address only.
3. The DNS check run reports one alias to add and nothing else.
4. The site check run reports one certificate to reissue, Grafana's, and no other.

**Result, 2026-10-10:** passed, with item 4 checked another way.

- `grafana.mobile.deevnet.net` answered `NXDOMAIN`.
- Grafana's certificate named `dv02obs001v01.mobile.deevnet.net` and `10.20.25.22` only.
- The DNS check run reported one alias to add, `grafana`, with 19 host overrides and 14 aliases
  unchanged.
- The site-wide check run was not used: these roles cannot be dry-run through a signing or an
  OpenBao login. Instead the certificate each of the eight `site_cert` services serves was compared
  with the names its role asks for. Grafana's lacked the new name; the API's, the state store's,
  Omada's, OpenBao's, the downloads site's, the broker's and the log store's lacked none.

**Undo:** nothing to undo.

### Step 2: The alias

Not disruptive.

**Run:**

```bash
cd ansible-collection-deevnet.net
ansible-playbook playbooks/dns.yml
```

**Verify:**

1. `dig @10.20.10.1 grafana.mobile.deevnet.net` answers `NOERROR` with `10.20.25.22`.
2. The same from `DVNTM-TD`.
3. `downloads.mobile.deevnet.net` and the host's own name answer as before.
4. A second run reports no change.

**Result, 2026-10-10:** passed.

- The run added one alias and reconfigured Unbound; nothing was updated or deleted.
- `grafana.mobile.deevnet.net` answers `NOERROR` with `10.20.25.22`, from the Builder and from a
  Mac on `DVNTM`.
- Twelve substrate names and two tenant names were asked before and after: `grafana` is the only
  answer that changed.
- A second run reported no change.
- From `DVNTM-TD` the name resolved and Grafana answered at it, seen after step 3.

**Undo:** remove the alias from inventory and run the playbook with `-e dns_delete_unmanaged=true`.

### Step 3: Grafana's certificate and root URL

Restarts Grafana once.

**Run:**

```bash
cd ../ansible-collection-deevnet.mgmt
ansible-playbook playbooks/site.yml --tags dashboards
```

**Verify:**

1. The served certificate names `grafana.mobile.deevnet.net`, the host and its address.
2. `curl --cacert <root> https://grafana.mobile.deevnet.net:3000/api/health` returns `200`.
3. The same by host name returns `200`.
4. A browser at the service name logs in and opens a dashboard with no warning, and the links stay
   on the service name.
5. A second run reissues nothing and does not restart Grafana.
6. The API, not yet redeployed, still reaches Grafana: a reconcile of `tdemo` reports its
   `dashboards` step as done.

**Result, 2026-10-10:** passed, except item 4, which was checked without a browser.

- The role reported the installed certificate lacked `grafana.mobile.deevnet.net` and reissued it.
  The served certificate now names `dv02obs001v01.mobile.deevnet.net`, `grafana.mobile.deevnet.net`
  and `10.20.25.22`, and expires 2027-10-10.
- `/api/health` returns `200` with verification on at both names, from the Builder, from `DVNTM`
  and from `DVNTM-TD`.
- A request for a dashboard with no session is redirected to the login page at the name it was
  asked at, service name or host name. Logged in as `mabell` over the API at the service name, the
  tenant's dashboard is returned. No browser session was opened.
- A second run changed nothing and did not restart Grafana.
- `tdemo` reconciled through the API while it still held the host name.

**Undo:** revert the `grafana` role's names and root URL, remove the installed certificate, and run
the tag again; the next run issues one with the host's names only.

### Step 4: The API hands out the service name

Restarts the API. Not disruptive to devices.

**Run:**

```bash
ansible-playbook playbooks/site.yml --limit deevnet_api
```

**Verify:**

1. As a tenant, `GET` of its own record shows `dashboard_url` as
   `https://grafana.mobile.deevnet.net:3000`.
2. A reconcile of `tdemo` reports its `dashboards` step as done, now through the service name.
3. `tdemo`'s Terraform plans no replacement of a dashboard, applies, and a second plan shows no
   changes.

**Result, 2026-10-10:** passed, with item 3 seen on `mabell` and not on `tdemo`.

- The run rewrote the API's environment and recreated its container. Its certificate was not
  reissued. `/version` answers v0.10.0.
- `tdemo` reconciled through the API, now by the service name.
- The `mabell` tenant's plan showed `dashboard_url` changing from the host name to
  `https://grafana.mobile.deevnet.net:3000` and nothing else: no dashboard or folder replaced. It
  applied, and a second plan showed no changes.

**Undo:** set `deevnet_api_grafana_url` back and redeploy; tenants are handed the host name again,
which never stopped working.

### Step 5: Tenants are told

Not disruptive.

**Run:** update [Dashboards](/docs/runbook/tenant/services/dashboards/) in the tenant guide to the
service name, and tell each tenant. A tenant does nothing unless it wrote the host name into its own
code: its next plan reads the new `dashboard_url`.

**Verify:**

1. The guide names no host for Grafana.
2. The documentation site builds without warnings.
3. The `mabell` tenant's next apply shows the Grafana provider's address changed and no dashboard
   replaced.

**Result, 2026-10-10:** the guide is changed; the tenants are not all told.

- [Dashboards](/docs/runbook/tenant/services/dashboards/) gives the service name, and
  [Build Verification](/docs/runbook/substrate/building-recovery/build-verification/) checks
  Grafana by it. The site builds without warnings.
- Item 3 is step 4's result.
- `mabell` knows, being where this started. `tdemo`, `eds` and `cdeever` have not been told; nothing
  of theirs breaks in the meantime.

**Undo:** revert the guide.

## Verification

Steps 2, 3 and 4 pass; the firewall plan shows no drift; the documentation site builds without
warnings.

**Result, 2026-10-10:** steps 2, 3 and 4 pass and the site builds. The firewall plan was not run:
nothing in this change touches a rule, and the plan's target is the guarded apply.

## Undo

Each step's own undo, in reverse. Nothing here removes anything a tenant holds: at every point the
host name still reaches Grafana with a certificate that names it, so the worst case is the site as
it is today.

## To discover

- Whether a certificate name no longer wanted should also cause a reissue, or only a missing one.
  This change needs only the second.
- ~~Whether Grafana, with its root URL changed, redirects requests made at the host name.~~
  **Found 2026-10-10:** it does not. A request at the host name is answered at the host name, and
  its login redirect stays there.
- Whether anything outside the tenant guide prints the host name for Grafana: the handover notes
  written for tenants admitted before [CHG-0024](/docs/changes/2026/0024-tenant-dashboards/), and
  the take-home Pi image's notes.

## Outcome

| When | Steps | What happened |
|---|---|---|
| 2026-10-10 05:29 EDT | 1 | Read-only checks passed: one alias to add, one certificate lacking a name |
| 2026-10-10 05:30 EDT | 2 | The alias published; no other answer changed |
| 2026-10-10 05:32 EDT | 3 | Grafana's certificate reissued with the service name; root URL changed |
| 2026-10-10 05:34 EDT | 4 | The API redeployed; tenants are handed the service name |
| 2026-10-10 | 5 | The tenant guide changed; `mabell` moved to the new address |

### Departures from the plan

- **Step 1 did not use a site-wide check run.** A check run of the `dashboards` tag stops at the
  signing task and one of the API at its OpenBao login, each having changed nothing. The served
  certificates were compared with the names asked for instead.
- **Grafana restarted twice in step 3, not once:** when its container was recreated for the new
  environment, and again by the certificate's handler.
- **Step 4 ran `--tags deevnet-api`, not `--limit deevnet_api`.** The limit would also have run the
  state store's play on the same VM.
- **Step 4's tenant check was `mabell`'s Terraform, not `tdemo`'s.**
- **No browser was used.** Step 3's fourth item was checked with requests that follow what a
  browser does up to the login page, and one authenticated request for a dashboard.
- **The firewall plan was not run.**
- **The playbooks ran from the Builder's inventory checkout on an unmerged branch**, with `main`
  merged into it to bring in the alias. That branch's own change, to workstations, is not read by
  any play this change ran.
- **Tenants other than `mabell` were not told**, before or after.

## Follow-ups

- [ ] Tell `tdemo`, `eds` and `cdeever` that the address changed and that the old one keeps working
- [x] The `mabell` tenant withdraws `grafana.mabell.mobile.deevnet.net` from its zone and its code.
  Done 2026-10-10, before this change ran
- [ ] The site resolver answers a tenant's CNAME into `mobile.deevnet.net` with `NXDOMAIN` for the
  target. Probably it follows the CNAME through ordinary resolution, which reaches the public
  `deevnet.net` and not its own host overrides; not confirmed. Decide whether tenants may publish
  such a CNAME at all, and say so in [DNS](/docs/runbook/tenant/services/dns/)
- [ ] The same service names for the log store and the state store, if wanted
