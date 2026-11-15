---
title: "Alerting"
weight: 6
---

# Alerting

{{< status-badge "active" "Available" >}}

## What you get

**Alert rules over your metrics and your logs, run by the platform under your own token, with each
alert sent to your phone while you are on site**
([ADR-0023](/docs/architecture/decisions/platform-services/0023-metrics-and-alerting/)). You
declare rules in groups, in Terraform. Your groups run in a vmalert of your own, which reads with
your `log_read_token`, so a rule sees exactly what your token sees and nothing of another tenant's.
When a rule fires, and again when it clears, Alertmanager sends a notification to your ntfy topic,
and the ntfy app on your phone shows it.

| You declare | You get |
|---|---|
| a [`deevnet_alert_rule_group`](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/alert_rule_group/), with a `topic` | its alerts on the ntfy topic `<tenant>-<topic>`, its `ntfy_topic` |
| nothing more: it comes with [`deevnet_tenant`](https://deevnet.github.io/terraform-provider-deevnet/docs/resources/tenant/) | a phone login, `notify_username` and `notify_password`, for the server `notify_endpoint` (`https://ntfy.mobile.deevnet.net`) |

Alerting needs provider 0.13 or later. A copy initialized with an earlier one runs
`terraform init -upgrade` once, then `terraform apply` to record the login.

## Rule groups

**A group is one `type` of rule, evaluated together, sent to one topic.**

```hcl
# Over your workloads' metrics: MetricsQL (PromQL works).
resource "deevnet_alert_rule_group" "backend" {
  tenant = deevnet_tenant.this.name
  name   = "backend"
  type   = "metrics"
  topic  = "backend"

  rule {
    alert       = "QueueBacklog"
    expr        = "backend_queue_depth > 100"
    for         = "5m"
    labels      = { severity = "page" }
    annotations = { summary = "The backend's queue is {{ $value }} deep" }
  }
}

# Over your devices' logs: LogsQL ending in a stats pipe.
resource "deevnet_alert_rule_group" "devices" {
  tenant    = deevnet_tenant.this.name
  name      = "devices"
  type      = "logs"
  partition = "devices"
  topic     = "devices"

  rule {
    alert       = "DeviceError"
    expr        = "error | stats by (device) count() as hits | filter hits:>0"
    annotations = { summary = "{{ $labels.device }} logged {{ $value }} errors" }
  }
}
```

- **`type`** is `metrics`, over your metrics, or `logs`, over your logs. A rule fires for each series,
  or each `stats` row, its expression returns.
- **`partition`** chooses what the rules read: `workloads` (the default), what your workloads push;
  `platform`, what the site publishes about your tenant; or `devices`, your devices' logs from MQTT,
  for a `logs` group only. All three are your own.
- **`interval`** is how often the group is evaluated, 30 seconds to an hour; `1m` by default.
- **`topic`** is the end of the ntfy topic. Several groups may share one.
- **Annotations** are the notification's text, with vmalert's templates: `{{ $value }}`,
  `{{ $labels.device }}`.

A group holds up to 50 rules, and a tenant up to 20 groups and 200 rules.

## What is refused

**The API refuses a rule before it records it, and the apply fails with the reason.**
- **A rule vmalert won't load:** the API has vmalert check every expression, and the apply shows the
  parse error.
- **A recording rule:** alerting rules only.
- **The labels `tenant`, `deevnet_topic` and `alertname`, and any label starting `__`:** the platform
  sets them, and the first two decide whose topic an alert goes to.

vmalert checks expressions in advance, but not annotation templates: see a new template in a real
notification before you rely on it.

## Your phone

**The ntfy app on an Android phone, on the site's network, shows your alerts.**
1. **Install the Deevnet Root CA on the phone,** as a CA certificate (*Settings → Security → Encryption
   & credentials → Install a certificate → CA certificate*, worded differently by maker). Use
   `deevnet-root-ca.pem` from your repository; name the copy `deevnet-root-ca.crt` if the phone
   won't offer the file. The ntfy app trusts a CA you install.
2. **Install ntfy** from Google Play or F-Droid.
3. **Subscribe to each topic** your groups name, `<tenant>-<topic>`, choosing another server:
   `notify_endpoint`. The app asks for a login: `notify_username` and `notify_password`. Read the
   password in the console, with `.backend.env` loaded:
   `echo 'nonsensitive(deevnet_tenant.this.notify_password)' | terraform console`.

The phone needs a network that reaches the site: your computer's Wi-Fi, `DVNTM-TD`, or a
[Wi-Fi key](/docs/runbook/tenant/services/wifi-keys/) of trust class `tenant_dev` declared for it.

Your login reads only the topics starting `<tenant>-`, and publishes to none of them: only the
platform's Alertmanager can, so a lost phone cannot send false alerts. ntfy keeps a topic's
messages for 12 hours, so a phone that was away catches up when it is back.

## Timing

- **A metrics rule sees a sample about 30 seconds after it arrives,** as a query does
  ([Metrics](/docs/runbook/tenant/services/metrics/#timing)), then waits its `for`, then up to one
  `interval`.
- **A logs rule searches only the last `interval`.** It suits "this happened" alerts: a line that
  arrived while nothing was evaluating, or longer ago than one interval, is never seen.
- **Alertmanager waits 30 seconds before an alert's first notification,** to gather others that fire
  with it. Changes to a firing group, its resolved notification included, go out at most every 5
  minutes, and an alert still firing is sent again every 4 hours.

## What it does not do yet

- **No iOS:** without a forward to ntfy.sh, iOS delivers *"hours"* late, and nothing leaves the site
  today. Off-site delivery is ADR-0023's open question 2.
- **No notifications off site:** the server is reachable only from the site's network.
- **No email or webhooks,** and no recording rules.
