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

/**
 * Ready Prediction Bundle かどうか。
 * - runners が1頭以上
 * - catalog projection / pending ではない
 */
export function isReadyPredictionBundle(bundle, meta = {}) {
  if (!bundle || typeof bundle !== "object") return false;
  if (isCatalogProjectionMeta(meta)) return false;
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
