/**
 * I-2 Analyzer Registry — event_type ごとに解析を分離。
 *
 * Contract (expect-root-cause/1.0):
 *   root_cause  — primary cause code
 *   confidence  — 0..1
 *   reason      — human-readable explanation
 *
 * Implemented analyzers only:
 *   miss | feature_missing | prediction_failed | result_sync_failed
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

/** @typedef {{ event_type: string, events: object[], run_id: string, output_dir: string }} AnalyzerContext */

function evidenceRefs(events) {
  return events.slice(0, 50).map((e) => ({
    event_id: e.event_id,
    event_type: e.event_type,
    path: e.path,
    fingerprint: e.fingerprint ?? null,
    race_date: e.race_date ?? null,
    race_id: e.race_id ?? null,
  }));
}

function topKey(map) {
  const entries = Object.entries(map);
  if (!entries.length) return null;
  entries.sort((a, b) => b[1] - a[1]);
  return entries[0][0];
}

function share(count, total) {
  if (!total) return 0;
  return Math.round((count / total) * 1000) / 1000;
}

/**
 * @param {AnalyzerContext} ctx
 */
export function analyzeMiss(ctx) {
  const byCategory = {};
  const byEngine = {};
  let highConfMiss = 0;
  const n = ctx.events.length;

  for (const ev of ctx.events) {
    const p = ev.payload || {};
    const cat = p.miss_category || "unknown";
    byCategory[cat] = (byCategory[cat] || 0) + 1;
    const eng = p.engine_source || "unknown";
    byEngine[eng] = (byEngine[eng] || 0) + 1;
    const conf = p.confidence;
    if (typeof conf === "number" && conf >= 80 && cat !== "unknown") {
      highConfMiss += 1;
    }
  }

  const dominant = topKey(byCategory) || "unknown";
  let root_cause = "miss_distribution_unclear";
  let confidence = 0.4;
  let reason = `Miss events=${n}; dominant category=${dominant}.`;

  if (dominant === "miss_top1") {
    root_cause = "ranking_near_miss_top1";
    confidence = Math.min(0.95, 0.55 + share(byCategory.miss_top1 || 0, n));
    reason =
      `Dominant miss_top1 (${byCategory.miss_top1}/${n}): winner near candidate pool but Top1 wrong. ` +
      `Prefer Top1 calibration; exclude feature_missing co-occurring races.`;
  } else if (dominant === "miss_top3") {
    root_cause = "ranking_mid_miss_top3";
    confidence = Math.min(0.9, 0.5 + share(byCategory.miss_top3 || 0, n));
    reason = `Dominant miss_top3 (${byCategory.miss_top3}/${n}): mid-rank miss.`;
  } else if (dominant === "miss_top5") {
    root_cause = "ranking_far_miss_top5";
    confidence = Math.min(0.9, 0.5 + share(byCategory.miss_top5 || 0, n));
    reason = `Dominant miss_top5 (${byCategory.miss_top5}/${n}): far miss — check features/engine before Core.`;
  }

  if (highConfMiss > 0 && dominant === "miss_top1") {
    root_cause = "calibration_high_confidence_near_miss";
    confidence = Math.min(0.97, confidence + 0.05);
    reason += ` High-confidence misses=${highConfMiss}.`;
  }

  return {
    schema_version: "expect-root-cause/1.0",
    event_type: "miss",
    analysis_id: `miss-${ctx.run_id}`,
    event_count: n,
    status: n ? "ok" : "empty",
    root_cause,
    confidence,
    reason,
    findings: {
      by_miss_category: byCategory,
      by_engine_source: byEngine,
      high_confidence_miss_count: highConfMiss,
      dominant_category: dominant,
    },
    evidence_refs: evidenceRefs(ctx.events),
    recommendation:
      root_cause.startsWith("ranking_") || root_cause.startsWith("calibration_")
        ? "Candidate for Core-targeted Proposal after Human Review (I-3)."
        : "Gather more miss Evidence before Core proposal.",
  };
}

/**
 * @param {AnalyzerContext} ctx
 */
export function analyzeFeatureMissing(ctx) {
  const byFallback = {};
  const byFeatureSource = {};
  const byEngine = {};
  const n = ctx.events.length;

  for (const ev of ctx.events) {
    const p = ev.payload || {};
    const fb = p.fallback_reason || "unknown";
    byFallback[fb] = (byFallback[fb] || 0) + 1;
    const fs = p.feature_source || "unknown";
    byFeatureSource[fs] = (byFeatureSource[fs] || 0) + 1;
    const eng = p.engine_source || "unknown";
    byEngine[eng] = (byEngine[eng] || 0) + 1;
  }

  const topFallback = topKey(byFallback) || "unknown";
  let root_cause = "feature_supply_unclear";
  let confidence = 0.4;
  let reason = `feature_missing events=${n}; top fallback_reason=${topFallback}.`;

  if (/market/i.test(topFallback)) {
    root_cause = "market_feature_absent";
    confidence = Math.min(0.95, 0.6 + share(byFallback[topFallback] || 0, n));
    reason = `Market feature gap (fallback=${topFallback}, ${byFallback[topFallback]}/${n}).`;
  } else if (/platform/i.test(topFallback)) {
    root_cause = "platform_or_etl_late";
    confidence = Math.min(0.95, 0.6 + share(byFallback[topFallback] || 0, n));
    reason = `Platform/ETL supply issue (fallback=${topFallback}, ${byFallback[topFallback]}/${n}).`;
  } else if (
    /feature_missing/i.test(topFallback) ||
    Object.keys(byFeatureSource).some((k) => /missing|none/i.test(k))
  ) {
    root_cause = "feature_source_missing_or_none";
    confidence = Math.min(0.92, 0.55 + share(byFallback[topFallback] || 0, n));
    reason =
      `feature_source missing/none or fallback_reason=feature_missing ` +
      `(top=${topFallback}, ${byFallback[topFallback] || 0}/${n}).`;
  }

  return {
    schema_version: "expect-root-cause/1.0",
    event_type: "feature_missing",
    analysis_id: `feature_missing-${ctx.run_id}`,
    event_count: n,
    status: n ? "ok" : "empty",
    root_cause,
    confidence,
    reason,
    findings: {
      by_fallback_reason: byFallback,
      by_feature_source: byFeatureSource,
      by_engine_source: byEngine,
      top_fallback_reason: topFallback,
    },
    evidence_refs: evidenceRefs(ctx.events),
    recommendation:
      "Data supply / metadata Proposal — Prediction Core out of scope.",
  };
}

/**
 * @param {AnalyzerContext} ctx
 */
export function analyzePredictionFailed(ctx) {
  const byReason = {};
  const n = ctx.events.length;
  for (const ev of ctx.events) {
    const r = ev.payload?.reason || "unknown";
    byReason[r] = (byReason[r] || 0) + 1;
  }
  const top = topKey(byReason) || "unknown";

  let root_cause = "prediction_failure_unclear";
  let confidence = 0.4;
  let reason = `prediction_failed events=${n}; top reason=${top}.`;

  if (/missing|not_found|no_prediction/i.test(top)) {
    root_cause = "prediction_absent";
    confidence = Math.min(0.95, 0.6 + share(byReason[top] || 0, n));
    reason = `Prediction absent for race (${top}, ${byReason[top]}/${n}).`;
  } else if (/bundle_invalid|invalid|parse/i.test(top)) {
    root_cause = "prediction_bundle_invalid";
    confidence = Math.min(0.95, 0.6 + share(byReason[top] || 0, n));
    reason = `Invalid prediction bundle (${top}, ${byReason[top]}/${n}).`;
  } else if (/resolve|race_id/i.test(top)) {
    root_cause = "race_id_resolution_failed";
    confidence = Math.min(0.9, 0.55 + share(byReason[top] || 0, n));
    reason = `Race identity resolution failed (${top}, ${byReason[top]}/${n}).`;
  }

  return {
    schema_version: "expect-root-cause/1.0",
    event_type: "prediction_failed",
    analysis_id: `prediction_failed-${ctx.run_id}`,
    event_count: n,
    status: n ? "ok" : "empty",
    root_cause,
    confidence,
    reason,
    findings: { by_reason: byReason, top_reason: top },
    evidence_refs: evidenceRefs(ctx.events),
    recommendation:
      "Pipeline / race_id remediation — not Core ranking change.",
  };
}

/**
 * @param {AnalyzerContext} ctx
 */
export function analyzeResultSyncFailed(ctx) {
  const byProvider = {};
  const byError = {};
  const n = ctx.events.length;
  for (const ev of ctx.events) {
    const p = ev.payload || {};
    const provider = p.provider || "unknown";
    byProvider[String(provider)] = (byProvider[String(provider)] || 0) + 1;
    const err = p.error || p.reason || "unknown";
    byError[String(err)] = (byError[String(err)] || 0) + 1;
  }
  const topErr = topKey(byError) || "unknown";
  const topProv = topKey(byProvider) || "unknown";

  let root_cause = "result_sync_unclear";
  let confidence = 0.4;
  let reason = `result_sync_failed events=${n}; provider=${topProv}; error=${topErr}.`;

  if (/not.?found|missing|enoent|csv/i.test(topErr)) {
    root_cause = "result_csv_or_source_missing";
    confidence = Math.min(0.95, 0.6 + share(byError[topErr] || 0, n));
    reason = `Result source/CSV missing (${topErr}, ${byError[topErr]}/${n}).`;
  } else if (/timeout|network|econn/i.test(topErr)) {
    root_cause = "result_provider_unreachable";
    confidence = Math.min(0.9, 0.55 + share(byError[topErr] || 0, n));
    reason = `ResultProvider unreachable (${topErr}, ${byError[topErr]}/${n}).`;
  } else if (/parse|format|schema/i.test(topErr)) {
    root_cause = "result_payload_parse_error";
    confidence = Math.min(0.9, 0.55 + share(byError[topErr] || 0, n));
    reason = `Result payload parse/format error (${topErr}, ${byError[topErr]}/${n}).`;
  }

  return {
    schema_version: "expect-root-cause/1.0",
    event_type: "result_sync_failed",
    analysis_id: `result_sync_failed-${ctx.run_id}`,
    event_count: n,
    status: n ? "ok" : "empty",
    root_cause,
    confidence,
    reason,
    findings: {
      by_provider: byProvider,
      by_error: byError,
      top_provider: topProv,
      top_error: topErr,
    },
    evidence_refs: evidenceRefs(ctx.events),
    recommendation: "ResultProvider / ops remediation — not Core scope.",
  };
}

/** @type {Record<string, function(AnalyzerContext): object>} */
export const ANALYZERS = {
  miss: analyzeMiss,
  feature_missing: analyzeFeatureMissing,
  prediction_failed: analyzePredictionFailed,
  result_sync_failed: analyzeResultSyncFailed,
};

export const REGISTERED_EVENT_TYPES = Object.freeze(Object.keys(ANALYZERS));

/**
 * @param {string} eventType
 */
export function getAnalyzer(eventType) {
  return ANALYZERS[eventType] || null;
}

/**
 * @param {object} scanResult
 * @param {string} devRoot
 * @param {string} runId
 */
export function runAnalyzers(scanResult, devRoot, runId) {
  /** @type {Record<string, object>} */
  const results = {};

  const byType = new Map();
  for (const ev of scanResult.events) {
    const t = ev.event_type;
    if (!byType.has(t)) byType.set(t, []);
    byType.get(t).push(ev);
  }

  for (const [eventType, events] of byType) {
    const fn = getAnalyzer(eventType);
    const outDir = join(devRoot, "analysis", eventType);
    mkdirSync(outDir, { recursive: true });

    if (!fn) {
      const skipped = {
        schema_version: "expect-root-cause/1.0",
        event_type: eventType,
        analysis_id: `unsupported-${runId}`,
        event_count: events.length,
        status: "unsupported",
        root_cause: "unsupported_event_type",
        confidence: 0,
        reason: `No analyzer registered for event_type=${eventType}; indexed only.`,
        policy: "index_only_skip_analysis",
        evidence_refs: evidenceRefs(events),
      };
      writeFileSync(
        join(outDir, `${runId}.json`),
        JSON.stringify(skipped, null, 2) + "\n",
        "utf8"
      );
      writeFileSync(
        join(outDir, "latest.json"),
        JSON.stringify(skipped, null, 2) + "\n",
        "utf8"
      );
      results[eventType] = skipped;
      continue;
    }

    const analysis = fn({
      event_type: eventType,
      events,
      run_id: runId,
      output_dir: outDir,
    });
    writeFileSync(
      join(outDir, `${runId}.json`),
      JSON.stringify(analysis, null, 2) + "\n",
      "utf8"
    );
    writeFileSync(
      join(outDir, "latest.json"),
      JSON.stringify(analysis, null, 2) + "\n",
      "utf8"
    );
    results[eventType] = analysis;
  }

  return results;
}
