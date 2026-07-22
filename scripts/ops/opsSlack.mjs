/**
 * Slack notification helper — SLK-N01 Critical / SLK-N02 Warning / SLK-N03 Recovery
 * 設計: docs/releases/v2-operations-monitoring-inventory.md §2.6
 * Webhook 未設定時は no-op。同一 Alert ID は 15 分抑制。
 */
const SUPPRESS_MS = 15 * 60 * 1000;
const _lastSent = new Map();

function resolveWebhook(severity, opts) {
  opts = opts || {};
  if (opts.webhookUrl) return opts.webhookUrl;
  if (severity === "warning") {
    return (
      process.env.OPS_SLACK_WEBHOOK_WARNING ||
      process.env.OPS_SLACK_WEBHOOK_URL ||
      ""
    );
  }
  if (severity === "recovery") {
    return (
      process.env.OPS_SLACK_WEBHOOK_WARNING ||
      process.env.OPS_SLACK_WEBHOOK_URL ||
      ""
    );
  }
  return (
    process.env.OPS_SLACK_WEBHOOK_CRITICAL ||
    process.env.OPS_SLACK_WEBHOOK_URL ||
    ""
  );
}

function suppressKey(severity, alertId) {
  return String(severity) + ":" + String(alertId);
}

/**
 * @param {"critical"|"warning"|"recovery"} severity
 * @param {object} alert
 * @param {object} [opts]
 */
export async function notifySlack(severity, alert, opts) {
  opts = opts || {};
  const url = resolveWebhook(severity, opts);
  if (!url) {
    return { sent: false, reason: "webhook_unset" };
  }
  const alertId = String((alert && alert.alert_id) || "unknown");
  const key = suppressKey(severity, alertId);
  const now = opts.now != null ? opts.now : Date.now();
  if (_lastSent.has(key)) {
    const prev = _lastSent.get(key);
    if (now - prev < SUPPRESS_MS) {
      return { sent: false, reason: "suppressed" };
    }
  }

  const icon =
    severity === "critical"
      ? ":rotating_light:"
      : severity === "warning"
        ? ":warning:"
        : ":white_check_mark:";
  const text = [
    icon + " *" + alertId + "* (" + severity + ")",
    alert.summary || alert.error || severity + " alert",
    alert.service ? "service: `" + alert.service + "`" : null,
    alert.runbook ? "runbook: " + alert.runbook : null,
  ]
    .filter(Boolean)
    .join("\n");

  const doFetch = opts.fetch || globalThis.fetch;
  try {
    const res = await doFetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      return { sent: false, reason: "http_" + res.status };
    }
    _lastSent.set(key, now);
    return { sent: true };
  } catch (e) {
    return { sent: false, reason: String(e && e.message ? e.message : e) };
  }
}

export async function notifySlackCritical(alert, opts) {
  return notifySlack("critical", alert, opts);
}

export async function notifySlackWarning(alert, opts) {
  return notifySlack("warning", alert, opts);
}

export async function notifySlackRecovery(alert, opts) {
  return notifySlack("recovery", alert, opts);
}

/** アラート配列を severity 別に通知（運用最終確認用） */
export async function dispatchAlerts(alerts, opts) {
  opts = opts || {};
  const results = [];
  for (const a of alerts || []) {
    if (!a || !a.active) continue;
    const sev = a.severity === "critical" ? "critical" : "warning";
    results.push(await notifySlack(sev, a, opts));
  }
  return results;
}

/** test helper */
export function _resetSlackSuppress() {
  _lastSent.clear();
}
