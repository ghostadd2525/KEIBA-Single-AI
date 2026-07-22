/**
 * BFF Slack notifier — Pages Secrets 経由（未設定は no-op）
 * EC2 scripts/ops/opsSlack.mjs と同等契約（SLK-N01/N02）
 */
const SUPPRESS_MS = 15 * 60 * 1000;
const _lastSent = new Map();

function webhookFor(env, severity) {
  env = env || {};
  if (severity === "warning" || severity === "recovery") {
    return String(env.OPS_SLACK_WEBHOOK_WARNING || env.OPS_SLACK_WEBHOOK_URL || "").trim();
  }
  return String(env.OPS_SLACK_WEBHOOK_CRITICAL || env.OPS_SLACK_WEBHOOK_URL || "").trim();
}

export function slackConfigured(env) {
  env = env || {};
  return {
    critical: Boolean(String(env.OPS_SLACK_WEBHOOK_CRITICAL || env.OPS_SLACK_WEBHOOK_URL || "").trim()),
    warning: Boolean(
      String(env.OPS_SLACK_WEBHOOK_WARNING || env.OPS_SLACK_WEBHOOK_URL || "").trim()
    ),
  };
}

/**
 * @param {object} context
 * @param {"critical"|"warning"|"recovery"} severity
 * @param {object} alert
 */
export async function notifySlack(context, severity, alert) {
  const env = (context && context.env) || {};
  const url = webhookFor(env, severity);
  if (!url) return { sent: false, reason: "webhook_unset" };

  const alertId = String((alert && alert.alert_id) || "unknown");
  const key = severity + ":" + alertId;
  const now = Date.now();
  if (_lastSent.has(key) && now - _lastSent.get(key) < SUPPRESS_MS) {
    return { sent: false, reason: "suppressed" };
  }

  const icon =
    severity === "critical"
      ? ":rotating_light:"
      : severity === "warning"
        ? ":warning:"
        : ":white_check_mark:";
  const text = [
    icon + " *" + alertId + "* (" + severity + ")",
    (alert && (alert.summary || alert.error)) || severity + " alert",
    alert && alert.service ? "service: `" + alert.service + "`" : null,
    alert && alert.runbook ? "runbook: " + alert.runbook : null,
  ]
    .filter(Boolean)
    .join("\n");

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) return { sent: false, reason: "http_" + res.status };
    _lastSent.set(key, now);
    return { sent: true };
  } catch (e) {
    return { sent: false, reason: String(e && e.message ? e.message : e) };
  }
}

export async function dispatchAlerts(context, alerts) {
  const results = [];
  for (const a of alerts || []) {
    if (!a || !a.active) continue;
    const sev = a.severity === "critical" ? "critical" : "warning";
    results.push(await notifySlack(context, sev, a));
  }
  return results;
}

export function _resetSlackSuppressForTests() {
  _lastSent.clear();
}
