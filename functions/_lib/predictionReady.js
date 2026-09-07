/**
 * Prediction Bundle の「成功（Ready）」判定（BFF 共通）
 *
 * 空 Projection / runners=[] は成功扱いにしない。
 * Prediction Engine / CE / AI ロジックには触れない。
 */

export function bundleRunners(bundle) {
  if (!bundle || typeof bundle !== "object") return [];
  const ev = bundle.evaluation || {};
  if (Array.isArray(ev.runners)) return ev.runners;
  if (Array.isArray(bundle.runners)) return bundle.runners;
  return [];
}

export function isCatalogProjectionMeta(meta = {}) {
  if (!meta || typeof meta !== "object") return false;
  if (meta.engine_source === "pi_catalog_projection") return true;
  if (meta.fallback_reason === "pi_prediction_unavailable_catalog_projection") return true;
  if (meta.prediction_status === "pending") return true;
  return false;
}

/** Polling しても解決しない恒久 unavailable（202 pending にしない） */
export function isTerminalUnavailableReason(reason) {
  const r = String(reason || "").trim().toLowerCase();
  if (!r) return false;
  if (r === "race_not_resolved" || r === "race_not_found" || r === "missing_race_id") {
    return true;
  }
  if (r === "input_not_ready" || r === "platform_missing") return true;
  return false;
}

export function isTerminalUnavailable(bundle, meta = {}) {
  const m = meta && typeof meta === "object" ? meta : {};
  const b = bundle && typeof bundle === "object" ? bundle : {};
  const reason = m.fallback_reason || b.fallback_reason || "";
  if (isTerminalUnavailableReason(reason)) return true;
  const state = String(m.fallback_state || "").toLowerCase();
  if (state.includes("race_not_resolved") || state.includes("race_not_found")) return true;
  const eng = String(m.engine_source || "");
  if (eng === "prediction_unavailable" && isTerminalUnavailableReason(reason)) return true;
  return false;
}

/** 一時的未準備 — 202 pending 継続可 */
export function isRetryableUnavailableReason(reason) {
  const r = String(reason || "").trim().toLowerCase();
  if (!r) return true;
  if (isTerminalUnavailableReason(r)) return false;
  if (
    r === "feature_not_ready" ||
    r === "feature_csv_missing" ||
    r === "feature_missing" ||
    r.startsWith("feature_") ||
    r === "pi_prediction_unavailable_pending" ||
    r === "empty_runners" ||
    r === "not_ready_prediction"
  ) {
    return true;
  }
  return false;
}

/**
 * Ready Prediction Bundle かどうか。
 * - runners が1頭以上
 * - catalog projection / pending / mock / unavailable ではない
 */
export function isReadyPredictionBundle(bundle, meta = {}) {
  if (!bundle || typeof bundle !== "object") return false;
  if (isCatalogProjectionMeta(meta)) return false;
  if (meta.prediction_available === false) return false;
  if (bundle.prediction_available === false) return false;
  const eng = String(meta.engine_source || "");
  if (eng === "prediction_unavailable" || eng === "mock_fallback" || eng === "bff_mock" || eng === "mock") {
    return false;
  }
  const fb = String(meta.fallback_state || meta.fallback_reason || "").toLowerCase();
  if (fb.includes("mock_fallback") || fb.includes("prediction_unavailable")) {
    return false;
  }
  const mv = String(meta.model_version || bundle.model_version || "").toLowerCase();
  if (mv.includes("dummy-model")) return false;
  if (bundle.model_version === "list-projection" && bundleRunners(bundle).length === 0) {
    return false;
  }
  return bundleRunners(bundle).length > 0;
}

/** Projection 抑止時の WARN ログ（Workers console） */
export function warnProjectionSuppressed(fields = {}) {
  const line = {
    level: "WARN",
    event: "Prediction Fetch Failed",
    detail: "Projection Returned",
    race_id: fields.race_id != null ? String(fields.race_id) : null,
    numeric_race_id:
      fields.numeric_race_id != null ? String(fields.numeric_race_id) : null,
    reason: fields.reason != null ? String(fields.reason) : "unknown",
    at: new Date().toISOString(),
  };
  console.warn(JSON.stringify(line));
  return line;
}
