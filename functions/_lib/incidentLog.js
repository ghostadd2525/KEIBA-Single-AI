/**
 * Phase OPS-Monitor — 障害インシデントログ
 *
 * Workers: console JSON 1行（Logpush / wrangler tail）
 * EC2: scripts/ops/monitor-prod.mjs → var/ops/incidents.jsonl
 */
export function writeIncident(context, evt) {
  const line = {
    incident: true,
    schema_version: "expect-ops-incident/1.0",
    occurred_at: new Date().toISOString(),
    service: String(evt.service || "unknown"),
    error: String(evt.error || ""),
    restart_count: Number(evt.restart_count) || 0,
    status: evt.status || "down",
    detail: evt.detail && typeof evt.detail === "object" ? evt.detail : {},
    source: evt.source || "bff",
    request_id:
      (context &&
        context.request &&
        context.request.headers &&
        (context.request.headers.get("cf-ray") || context.request.headers.get("x-request-id"))) ||
      null,
  };
  console.log(JSON.stringify(line));
  return line;
}

/**
 * @param {object} context
 * @param {Array<{name:string, ok:boolean, error?:string, restart_count?:number, status?:string, detail?:object}>} checks
 */
export function logFailedChecks(context, checks) {
  const lines = [];
  (checks || []).forEach(function (c) {
    if (c && c.ok === false) {
      lines.push(
        writeIncident(context, {
          service: c.name,
          error: c.error || "check failed",
          restart_count: c.restart_count || 0,
          status: c.status || "down",
          detail: c.detail || {},
          source: "bff",
        })
      );
    }
  });
  return lines;
}
