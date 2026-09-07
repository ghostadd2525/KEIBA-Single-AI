/**
 * I4 — unit check for singleDetailObservability (Node ESM).
 * Run: node scripts/ops/test-single-detail-observability.mjs
 */
import {
  recordSingleDetailEvent,
  snapshotSingleDetailMetrics,
  evaluateSingleDetailAlerts,
  _resetSingleDetailMetricsForTest,
  DEFAULT_THRESHOLDS,
} from "../../functions/_lib/singleDetailObservability.js";

function assert(cond, msg) {
  if (!cond) throw new Error(msg || "assertion failed");
}

_resetSingleDetailMetricsForTest();

// Expected fallback should not trip ALT-SD04
for (let i = 0; i < 25; i++) {
  recordSingleDetailEvent({
    latency_ms: 100,
    detail_source: "prediction_fallback",
    single_attempted: false,
    fallback_reason: "CORE_PAYLOAD_REQUIRED",
    http_status: 200,
  });
}
let snap = snapshotSingleDetailMetrics();
assert(snap.expected_fallback === 25, "expected_fallback count");
assert(snap.error_fallback === 0, "no error fallback");
let ev = evaluateSingleDetailAlerts(DEFAULT_THRESHOLDS, snap);
assert(!ev.deferred, "sample gate passed");
assert(
  !ev.alerts.some((a) => a.alert_id === "ALT-SD04"),
  "ALT-SD04 must ignore expected fallback"
);

_resetSingleDetailMetricsForTest();
for (let i = 0; i < 20; i++) {
  recordSingleDetailEvent({
    latency_ms: 9000,
    detail_source: "prediction_fallback",
    single_attempted: true,
    fallback_reason: "TIMEOUT",
    http_status: 504,
    timed_out: true,
  });
}
snap = snapshotSingleDetailMetrics();
ev = evaluateSingleDetailAlerts(DEFAULT_THRESHOLDS, snap);
const ids = ev.alerts.map((a) => a.alert_id);
assert(ids.includes("ALT-SD01"), "latency alert");
assert(ids.includes("ALT-SD02"), "timeout alert");
assert(ids.includes("ALT-SD03"), "5xx alert");
assert(ids.includes("ALT-SD04"), "error fallback alert");

console.log("PASS single-detail-observability", { alerts: ids, rates: snap.rates });
