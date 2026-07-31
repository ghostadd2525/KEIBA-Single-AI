/**
 * I4 — Single Detail operational metrics + alert evaluation (BFF)
 *
 * Does not modify Core / Consumer / Prediction / UI.
 * Records outcomes of /api/single/detail/:raceId resolutions.
 */
const SCHEMA = "expect-single-detail-metrics/1.0";

const EXPECTED_FALLBACK_REASONS = {
  CORE_PAYLOAD_REQUIRED: true,
  AI_BASE_URL_MISSING: true,
};

/** @type {{
 *  started_at: number,
 *  requests_total: number,
 *  flag_path_hits: number,
 *  single_attempted: number,
 *  single_success: number,
 *  prediction_fallback: number,
 *  expected_fallback: number,
 *  error_fallback: number,
 *  timeouts: number,
 *  http_errors: number,
 *  status_5xx: number,
 *  latency_ms_sum: number,
 *  latency_samples: number[],
 *  by_fallback_reason: Record<string, number>,
 * }} */
const STATE = {
  started_at: Date.now(),
  requests_total: 0,
  flag_path_hits: 0,
  single_attempted: 0,
  single_success: 0,
  prediction_fallback: 0,
  expected_fallback: 0,
  error_fallback: 0,
  timeouts: 0,
  http_errors: 0,
  status_5xx: 0,
  latency_ms_sum: 0,
  latency_samples: [],
  by_fallback_reason: {},
};

const MAX_SAMPLES = 200;

/**
 * @param {{
 *  latency_ms: number,
 *  detail_source?: string,
 *  single_attempted?: boolean,
 *  fallback_reason?: string|null,
 *  http_status?: number|null,
 *  timed_out?: boolean,
 * }} ev
 */
export function recordSingleDetailEvent(ev) {
  const latency = Number(ev.latency_ms) || 0;
  STATE.requests_total += 1;
  STATE.flag_path_hits += 1; // endpoint is only used when Flag ON path is taken
  STATE.latency_ms_sum += latency;
  STATE.latency_samples.push(latency);
  if (STATE.latency_samples.length > MAX_SAMPLES) {
    STATE.latency_samples.shift();
  }

  if (ev.single_attempted) {
    STATE.single_attempted += 1;
  }

  if (ev.timed_out || ev.fallback_reason === "TIMEOUT") {
    STATE.timeouts += 1;
  }

  const status = ev.http_status != null ? Number(ev.http_status) : null;
  if (status != null && status >= 500) {
    STATE.status_5xx += 1;
  }

  const reason = ev.fallback_reason ? String(ev.fallback_reason) : null;

  if (ev.detail_source === "single") {
    STATE.single_success += 1;
  } else if (ev.detail_source === "prediction_fallback" || reason) {
    STATE.prediction_fallback += 1;
    if (reason) {
      STATE.by_fallback_reason[reason] = (STATE.by_fallback_reason[reason] || 0) + 1;
    }
    if (reason && EXPECTED_FALLBACK_REASONS[reason]) {
      STATE.expected_fallback += 1;
    } else if (ev.single_attempted) {
      STATE.error_fallback += 1;
      STATE.http_errors += 1;
    } else if (
      reason === "SINGLE_DETAIL_ERROR" ||
      reason === "PREDICTION_ERROR_RESPONSE"
    ) {
      STATE.http_errors += 1;
    }
  }

  // Structured ops log (stdout / CF log)
  try {
    console.log(
      "[single-detail-ops] " +
        JSON.stringify({
          ts: new Date().toISOString(),
          layer: "single_detail",
          event: "resolve",
          latency_ms: Math.round(latency * 1000) / 1000,
          detail_source: ev.detail_source || null,
          single_attempted: !!ev.single_attempted,
          fallback_reason: reason,
          http_status: status,
          timed_out: !!ev.timed_out,
        })
    );
  } catch {
    /* ignore */
  }
}

function percentile(samples, p) {
  if (!samples.length) return 0;
  const sorted = samples.slice().sort(function (a, b) {
    return a - b;
  });
  const idx = Math.min(sorted.length - 1, Math.max(0, Math.ceil((p / 100) * sorted.length) - 1));
  return sorted[idx];
}

export function snapshotSingleDetailMetrics() {
  const n = STATE.requests_total || 0;
  const attempted = STATE.single_attempted || 0;
  const avg = STATE.latency_samples.length
    ? STATE.latency_ms_sum / STATE.latency_samples.length
    : 0;
  const fallbackRate = n ? STATE.prediction_fallback / n : 0;
  const expectedFallbackRate = n ? STATE.expected_fallback / n : 0;
  const errorFallbackRate = attempted ? STATE.error_fallback / attempted : 0;
  const timeoutRate = n ? STATE.timeouts / n : 0;
  const singleRate = n ? STATE.single_success / n : 0;
  const httpErrorRate = n ? STATE.http_errors / n : 0;
  // Flag ON rate ≈ share of detail resolutions hitting this endpoint.
  // Absolute ON rate vs all page views requires FE beacon (out of I4 UI freeze).
  const flagOnPathRate = n ? STATE.flag_path_hits / n : 0;

  return {
    schema_version: SCHEMA,
    uptime_sec: Math.round((Date.now() - STATE.started_at) / 1000),
    requests_total: STATE.requests_total,
    flag_path_hits: STATE.flag_path_hits,
    single_attempted: STATE.single_attempted,
    single_success: STATE.single_success,
    prediction_fallback: STATE.prediction_fallback,
    expected_fallback: STATE.expected_fallback,
    error_fallback: STATE.error_fallback,
    timeouts: STATE.timeouts,
    http_errors: STATE.http_errors,
    status_5xx: STATE.status_5xx,
    latency_ms_avg: Math.round(avg * 100) / 100,
    latency_ms_p50: percentile(STATE.latency_samples, 50),
    latency_ms_p95: percentile(STATE.latency_samples, 95),
    rates: {
      flag_on_path: Math.round(flagOnPathRate * 10000) / 10000,
      single_success: Math.round(singleRate * 10000) / 10000,
      prediction_fallback: Math.round(fallbackRate * 10000) / 10000,
      expected_fallback: Math.round(expectedFallbackRate * 10000) / 10000,
      error_fallback_of_attempted: Math.round(errorFallbackRate * 10000) / 10000,
      timeout: Math.round(timeoutRate * 10000) / 10000,
      http_error: Math.round(httpErrorRate * 10000) / 10000,
    },
    by_fallback_reason: { ...STATE.by_fallback_reason },
  };
}

/** Alert thresholds (documented in alert rules). Overridable via env in evaluate. */
export const DEFAULT_THRESHOLDS = {
  latency_p95_ms: 8000,
  timeout_rate: 0.05,
  /** Among Single attempts only — excludes expected CORE_PAYLOAD_REQUIRED */
  error_fallback_rate: 0.5,
  http_error_rate: 0.1,
  status_5xx_min: 3,
  min_requests: 20,
  min_single_attempts: 10,
};

/**
 * @param {object} [thresholds]
 * @param {object} [metrics]
 */
export function evaluateSingleDetailAlerts(thresholds, metrics) {
  const t = { ...DEFAULT_THRESHOLDS, ...(thresholds || {}) };
  const m = metrics || snapshotSingleDetailMetrics();
  const alerts = [];
  const n = m.requests_total || 0;

  if (n < t.min_requests) {
    return {
      alerts,
      deferred: true,
      reason: "insufficient_sample",
      min_requests: t.min_requests,
      requests_total: n,
    };
  }

  if ((m.latency_ms_p95 || 0) > t.latency_p95_ms) {
    alerts.push({
      alert_id: "ALT-SD01",
      severity: "warning",
      title: "Single Detail latency p95 high",
      message: `p95=${m.latency_ms_p95}ms > ${t.latency_p95_ms}ms`,
      runbook: "docs/ops/single-detail-runbook.md#alt-sd01",
    });
  }
  if ((m.rates && m.rates.timeout) > t.timeout_rate) {
    alerts.push({
      alert_id: "ALT-SD02",
      severity: "critical",
      title: "Single Detail timeout rate high",
      message: `timeout_rate=${m.rates.timeout} > ${t.timeout_rate}`,
      runbook: "docs/ops/single-detail-runbook.md#alt-sd02",
    });
  }
  if ((m.status_5xx || 0) >= t.status_5xx_min) {
    alerts.push({
      alert_id: "ALT-SD03",
      severity: "critical",
      title: "Single Detail 5xx observed",
      message: `status_5xx=${m.status_5xx}`,
      runbook: "docs/ops/single-detail-runbook.md#alt-sd03",
    });
  }
  const attempted = m.single_attempted || 0;
  if (
    attempted >= t.min_single_attempts &&
    m.rates &&
    m.rates.error_fallback_of_attempted > t.error_fallback_rate
  ) {
    alerts.push({
      alert_id: "ALT-SD04",
      severity: "warning",
      title: "Single Detail error fallback rate high",
      message:
        `error_fallback_of_attempted=${m.rates.error_fallback_of_attempted}` +
        ` > ${t.error_fallback_rate} (prediction_fallback=${m.prediction_fallback})`,
      runbook: "docs/ops/single-detail-runbook.md#alt-sd04",
    });
  }
  if ((m.rates && m.rates.http_error) > t.http_error_rate) {
    alerts.push({
      alert_id: "ALT-SD05",
      severity: "warning",
      title: "Single Detail HTTP error rate high",
      message: `http_error_rate=${m.rates.http_error} > ${t.http_error_rate}`,
      runbook: "docs/ops/single-detail-runbook.md#alt-sd05",
    });
  }

  return { alerts, deferred: false, metrics: m };
}

/** @internal test helper */
export function _resetSingleDetailMetricsForTest() {
  STATE.started_at = Date.now();
  STATE.requests_total = 0;
  STATE.flag_path_hits = 0;
  STATE.single_attempted = 0;
  STATE.single_success = 0;
  STATE.prediction_fallback = 0;
  STATE.expected_fallback = 0;
  STATE.error_fallback = 0;
  STATE.timeouts = 0;
  STATE.http_errors = 0;
  STATE.status_5xx = 0;
  STATE.latency_ms_sum = 0;
  STATE.latency_samples = [];
  STATE.by_fallback_reason = {};
}
