/**
 * PredictionAdapter — PredictionBundle 取得の差し替え点
 *
 * 契約（single-prediction-bundle/2.0）・HTTP API は変更しない。
 * V1.1: PI_BASE_URL 設定時は PI /v1/predictions を正とし mock_fallback しない。
 * 開発のみ: PI/AI 未設定時は ASSETS mock（bff_mock）。
 */
import { aiFetch, loadAssetJson } from "../aiProxy.js";
import { resolveCanonicalRaceRef } from "../canonicalRaceId.js";
import { catalogToPredictionBundle, normalizePredictionBundle } from "../domain.js";
import { getEnv, useAiProxy } from "../env.js";
import { mapPiPredictionToBundle, piProvenanceItem } from "../piPredictionMapper.js";
import { piFetch, usePiProxy } from "../piProxy.js";
import {
  isReadyPredictionBundle,
  isTerminalUnavailable,
  isRetryableUnavailableReason,
  warnProjectionSuppressed,
} from "../predictionReady.js";
import { findPiRaceInCatalog } from "../raceIdResolve.js";
import { normalizeRaceIdYear } from "../raceIdYear.js";

/** Public prediction timeout (restored V2 cold ~12–17s). */
function predictionTimeoutMs(env) {
  const n = Number(env?.PUBLIC_PREDICTION_TIMEOUT_MS || 30000);
  return Number.isFinite(n) && n >= 30000 ? n : 30000;
}

/** 空 Projection を pending として返す（成功 Bundle にはしない） */
function pendingPredictionResult({
  raceId,
  numericRaceId = null,
  reason = "pi_prediction_unavailable",
  requestedRaceId = undefined,
  yearCorrected = undefined,
  piError = undefined,
}) {
  warnProjectionSuppressed({
    race_id: raceId,
    numeric_race_id: numericRaceId,
    reason,
  });
  return {
    ok: false,
    pending: true,
    status: 202,
    error: "Prediction pending",
    code: "PREDICTION_PENDING",
    provenanceMeta: {
      engine: "n/a",
      engine_source: "pi_catalog_projection",
      prediction_status: "pending",
      race_id: raceId,
      numeric_race_id: numericRaceId || null,
      requested_race_id: requestedRaceId,
      year_corrected: yearCorrected,
      fallback_reason: "pi_prediction_unavailable_pending",
      reason,
      pi_error: piError,
    },
  };
}

/** 恒久 unavailable — 202 pending にせず Bundle をそのまま返す */
function terminalUnavailableResult(result, raceId) {
  const meta = result.provenanceMeta || {};
  const reason = meta.fallback_reason || "prediction_unavailable";
  warnProjectionSuppressed({
    race_id: raceId,
    numeric_race_id: meta.numeric_race_id || null,
    reason: `terminal:${reason}`,
  });
  return {
    ok: true,
    bundle: result.bundle,
    source: result.source,
    provider: result.provider,
    terminalUnavailable: true,
    provenanceMeta: {
      ...meta,
      prediction_status: "unavailable",
      prediction_available: false,
      reason,
    },
  };
}

/** 成功応答のガード: 空 runners / projection は pending に落とす（terminal は除外） */
function guardReadyOrPending(result, raceId) {
  if (!result || !result.ok) return result;
  const meta = result.provenanceMeta || {};
  if (isReadyPredictionBundle(result.bundle, meta)) return result;
  if (isTerminalUnavailable(result.bundle, meta)) {
    return terminalUnavailableResult(result, raceId);
  }
  const retryReason =
    meta.fallback_reason ||
    (bundleRunnersLen(result.bundle) === 0 ? "empty_runners" : "not_ready_prediction");
  if (!isRetryableUnavailableReason(retryReason)) {
    return terminalUnavailableResult(result, raceId);
  }
  return pendingPredictionResult({
    raceId: raceId || (result.bundle && result.bundle.race_id) || meta.race_id,
    numericRaceId: meta.numeric_race_id || null,
    reason:
      meta.fallback_reason ||
      (bundleRunnersLen(result.bundle) === 0
        ? "empty_runners"
        : "not_ready_prediction"),
    piError: meta.pi_error,
  });
}

function bundleRunnersLen(bundle) {
  const ev = (bundle && bundle.evaluation) || {};
  const runners = Array.isArray(ev.runners) ? ev.runners : [];
  return runners.length;
}

function bffMockItem(bundle) {
  return {
    race_id: bundle.race_id,
    engine_source: "bff_mock",
    fallback_reason: "bff_assets_only",
    model_version: bundle.model_version ?? null,
    inference_generated_at: bundle.generated_at ?? null,
  };
}

/** Python /v1 meta → BFF envelope 用（list） */
export function mergeListProvenanceMeta(base, provenanceMeta = {}) {
  const items = Array.isArray(provenanceMeta.items) ? provenanceMeta.items : [];
  return {
    ...base,
    engine: provenanceMeta.engine ?? "n/a",
    engine_source: provenanceMeta.engine_source ?? undefined,
    items,
  };
}

/** Python /v1 meta → BFF envelope 用（get） */
export function mergeGetProvenanceMeta(base, provenanceMeta = {}) {
  const next = {
    ...base,
    engine: provenanceMeta.engine ?? "n/a",
    engine_source: provenanceMeta.engine_source ?? "bff_mock",
    model_version: provenanceMeta.model_version ?? null,
    inference_generated_at: provenanceMeta.inference_generated_at ?? null,
  };
  for (const key of [
    "race_id",
    "core_race_id",
    "numeric_race_id",
    "feature_source",
    "fallback_reason",
    "detail",
    "reason",
    "decision_authority",
    "canonical_race_id",
    "source_race_id",
    "race_type",
    "fallback_state",
    "prediction_available",
    "feature_lookup_key",
  ]) {
    if (provenanceMeta[key] != null) next[key] = provenanceMeta[key];
  }
  return next;
}

function normalizeEngineSource(source) {
  if (source === "real_ai") return "real";
  return source;
}

async function fetchFromPiGet(context, raceId, catalogRace = null, opts = {}) {
  // 詳細は余裕を持たせる。一覧ファンアウト時だけ短く切る
  const timeoutMs =
    typeof opts.timeoutMs === "number" && opts.timeoutMs > 0 ? opts.timeoutMs : 20000;
  const proxied = await piFetch(
    context,
    `/v1/predictions/${encodeURIComponent(raceId)}`,
    { timeoutMs }
  );
  if (proxied instanceof Response) {
    // タイムアウト/不通はソフト失敗扱い（errorResponse だと後続 AI が遅延しうる）
    const status = proxied.status;
    let code = "PI_ERROR";
    try {
      const body = await proxied.clone().json();
      code = (body && body.error && body.error.code) || code;
    } catch {
      /* ignore */
    }
    return {
      ok: false,
      error: code === "PI_TIMEOUT" ? "PI prediction timeout" : "PI prediction failed",
      status: status || 502,
    };
  }
  if (!proxied || !proxied.ok) {
    return { ok: false, error: "PI prediction fetch failed", status: 502 };
  }

  const payload = proxied.payload;
  if (!payload || payload.prediction_available !== true) {
    return {
      ok: false,
      error: (payload && payload.error) || "prediction unavailable",
      status: 404,
      detail: payload && payload.message,
    };
  }

  const row = catalogRace || findPiRaceInCatalog({ races: [payload] }, raceId) || payload;
  const bundle = mapPiPredictionToBundle(payload, row, { context });
  if (!bundle) {
    return { ok: false, error: "PI prediction mapping failed", status: 502 };
  }

  return {
    ok: true,
    bundle,
    source: "pi-keibanet-api",
    provider: "pi",
    provenanceMeta: {
      engine: "real",
      engine_source: "pi",
      race_id: raceId,
      model_version: bundle.model_version,
      inference_generated_at: bundle.generated_at,
      numeric_race_id: payload.numeric_race_id || row.numeric_race_id || null,
    },
  };
}

async function fetchFromPiList(context, query = {}) {
  const date = String(query.date || "").trim();
  if (!date) {
    return { ok: false, error: "date query required for PI prediction list", status: 400 };
  }

  const qs = new URLSearchParams({ date });
  const catalogProxied = await piFetch(context, `/v1/races?${qs.toString()}`);
  if (catalogProxied instanceof Response) {
    return { ok: false, errorResponse: catalogProxied };
  }
  if (!catalogProxied || !catalogProxied.ok) {
    return { ok: false, error: "PI race catalog unavailable", status: 502 };
  }

  let races = Array.isArray(catalogProxied.payload.races) ? catalogProxied.payload.races : [];
  if (query.venue && query.venue !== "すべて") {
    races = races.filter((r) => (r.course || r.venue) === query.venue);
  }

  const bundles = [];
  const items = [];
  // 逐次だと日付一覧が数十秒かかるため並列取得（上限付き）
  // PI 予想が重い日は全件取得しない（ホーム固着防止）
  const MAX_LIST = 4;
  const slice = races.slice(0, MAX_LIST);
  const CONCURRENCY = 4;
  for (let i = 0; i < slice.length; i += CONCURRENCY) {
    const chunk = slice.slice(i, i + CONCURRENCY);
    const results = await Promise.all(
      chunk.map((race) => {
        const rid = String(race.race_id || "");
        if (!rid) return Promise.resolve(null);
        return fetchFromPiGet(context, rid, race, { timeoutMs: 4000 }).then((one) => ({
          race,
          rid,
          one,
        }));
      })
    );
    for (const row of results) {
      if (!row || !row.one || !row.one.ok) continue;
      if (
        !isReadyPredictionBundle(row.one.bundle, row.one.provenanceMeta || { engine_source: "pi" })
      ) {
        continue;
      }
      bundles.push(row.one.bundle);
      items.push(
        piProvenanceItem(row.rid, row.one.bundle, {
          numeric_race_id: row.race.numeric_race_id || null,
        })
      );
    }
  }

  // 空 Projection（runners=[] / pi_catalog_projection）は一覧の成功 Bundle にしない。
  // レースカード自体は /api/race-cards・カタログ経路を使う。
  if (!bundles.length) {
    if (races.length) {
      warnProjectionSuppressed({
        race_id: String(races[0].race_id || date),
        numeric_race_id: races[0].numeric_race_id || null,
        reason: "pi_list_all_unavailable_no_projection",
      });
    }
    return {
      ok: false,
      pending: true,
      status: 202,
      error: "Prediction list pending",
      code: "PREDICTION_PENDING",
      provenanceMeta: {
        engine: "n/a",
        engine_source: "pi_catalog_projection",
        prediction_status: "pending",
        reason: "pi_list_all_unavailable_no_projection",
        date,
      },
    };
  }

  return {
    ok: true,
    bundles,
    source: "pi-keibanet-api",
    provider: "pi",
    provenanceMeta: {
      engine: "real",
      engine_source: "pi",
      items,
    },
  };
}

async function fetchFromPythonList(context, query) {
  const qs = new URLSearchParams();
  if (query.date) qs.set("date", query.date);
  if (query.venue) qs.set("venue", query.venue);
  const q = qs.toString() ? `?${qs}` : "";
  const proxied = await aiFetch(context, "/v1/predictions" + q);
  if (proxied && proxied instanceof Response) {
    return { ok: false, errorResponse: proxied };
  }
  if (!proxied || !proxied.ok) return null;
  const raw = proxied.payload.data != null ? proxied.payload.data : proxied.payload;
  const rows = Array.isArray(raw) ? raw : raw.items || [];
  const meta = proxied.payload.meta || {};
  const provItems = Array.isArray(meta.items) ? meta.items : [];
  return {
    ok: true,
    bundles: rows.map((b) => normalizePredictionBundle(b, b.race_id)),
    source: "single-ai",
    provider: "python",
    provenanceMeta: {
      ...meta,
      engine: meta.engine || "real",
      engine_source: normalizeEngineSource(provItems[0]?.engine_source || "real"),
      items: provItems.map((it) => ({
        ...it,
        engine_source: normalizeEngineSource(it.engine_source),
      })),
    },
  };
}

async function fetchFromMockList(context, query) {
  const catalog = await loadAssetJson(context, "/data/mocks/races.json");
  if (!catalog) return { ok: false, error: "race catalog not found", status: 500 };

  let races = catalog.races || [];
  if (query.date) races = races.filter((r) => r.date === query.date);
  if (query.venue && query.venue !== "すべて") {
    races = races.filter((r) => r.venue === query.venue);
  }

  const template = await loadAssetJson(context, "/data/mocks/bundle-20260719_hanshin_11.json");
  const items = [];
  for (const race of races) {
    const full = await loadAssetJson(context, `/data/mocks/bundle-${race.race_id}.json`);
    if (full) items.push(normalizePredictionBundle(full, race.race_id));
    else items.push(catalogToPredictionBundle(race, template));
  }
  return {
    ok: true,
    bundles: items,
    source: "mock",
    provider: "mock",
    provenanceMeta: {
      engine: "n/a",
      items: items.map(bffMockItem),
    },
  };
}

async function fetchFromPythonGet(context, raceId, opts = {}) {
  const env = getEnv(context);
  const timeoutMs =
    typeof opts.timeoutMs === "number" && opts.timeoutMs > 0
      ? opts.timeoutMs
      : predictionTimeoutMs(env);
  const proxied = await aiFetch(context, `/v1/predictions/${encodeURIComponent(raceId)}`, {
    timeoutMs,
  });
  if (proxied && proxied instanceof Response) {
    return { ok: false, errorResponse: proxied };
  }
  if (!proxied || !proxied.ok) return null;
  const data = proxied.payload.data != null ? proxied.payload.data : proxied.payload;
  const meta = proxied.payload.meta || {};
  const explainMeta = (data && data.explain && data.explain.meta) || {};
  const decision_authority =
    data?.decision_authority || meta.decision_authority || explainMeta.decision_authority || null;
  const fallback_reason =
    data?.fallback_reason || meta.fallback_reason || explainMeta.fallback_reason || null;
  return {
    ok: true,
    bundle: normalizePredictionBundle(data, raceId),
    source: "single-ai",
    provider: "python",
    provenanceMeta: {
      ...meta,
      engine: meta.engine || "real",
      engine_source: normalizeEngineSource(meta.engine_source || "real_ai"),
      decision_authority,
      fallback_reason,
      fallback_state:
        meta.fallback_state ||
        (fallback_reason
          ? `fallback:${fallback_reason}`
          : decision_authority === "RESTORED_V2"
            ? "restored_v2"
            : decision_authority === "CURRENT_PATH"
              ? "current_path"
              : null),
      model_version: meta.model_version || data?.model_version || null,
      race_type: meta.race_type || null,
      canonical_race_id: meta.canonical_race_id || opts.canonical_race_id || null,
      source_race_id: meta.source_race_id || opts.source_race_id || raceId,
      core_race_id: meta.core_race_id || explainMeta.core_race_id || null,
    },
  };
}

async function fetchFromMockGet(context, raceId) {
  let bundle = await loadAssetJson(context, `/data/mocks/bundle-${raceId}.json`);
  if (!bundle) {
    const catalog = await loadAssetJson(context, "/data/mocks/races.json");
    const race = ((catalog && catalog.races) || []).find((r) => r.race_id === raceId);
    const template = await loadAssetJson(context, "/data/mocks/bundle-20260719_hanshin_11.json");
    if (race && template) {
      bundle = catalogToPredictionBundle(race, template);
    } else if (template) {
      bundle = normalizePredictionBundle(template, raceId);
    } else {
      return { ok: false, error: "PredictionBundle not found", status: 404 };
    }
  } else {
    bundle = normalizePredictionBundle(bundle, raceId);
  }
  const item = bffMockItem(bundle);
  return {
    ok: true,
    bundle,
    source: "mock",
    provider: "mock",
    provenanceMeta: {
      engine: "n/a",
      engine_source: "bff_mock",
      model_version: item.model_version,
      inference_generated_at: item.inference_generated_at,
      race_id: raceId,
    },
  };
}

/** 一覧: AI Bundle 優先 →（AI 未設定時のみ）PI → mock */
export async function adaptPredictionList(context, query = {}) {
  const env = getEnv(context);
  if (useAiProxy(env)) {
    const fromPy = await fetchFromPythonList(context, query);
    if (fromPy && fromPy.ok) return fromPy;
    if (fromPy && fromPy.errorResponse) return fromPy;
    return { ok: false, error: "Prediction list unavailable", status: 502 };
  }
  if (usePiProxy(env)) {
    return fetchFromPiList(context, query);
  }
  return fetchFromMockList(context, query);
}

/**
 * 1件: canonicalize → :8000 Bundle（primary）.
 * PI prediction is NOT silent fallback. Optional only when PREDICTION_ALLOW_PI_FALLBACK=1.
 */
export async function adaptPredictionGet(context, raceId) {
  const env = getEnv(context);
  const normalizedId = normalizeRaceIdYear(raceId);
  const idChanged = normalizedId && normalizedId !== String(raceId || "").trim();
  const sourceId = normalizedId || String(raceId || "").trim();

  if (useAiProxy(env)) {
    const ref = await resolveCanonicalRaceRef(aiFetch, context, sourceId);
    const predictId =
      ref.canonical_race_id ||
      ref.core_race_id ||
      sourceId;
    const fromPy = await fetchFromPythonGet(context, predictId, {
      timeoutMs: predictionTimeoutMs(env),
      canonical_race_id: ref.canonical_race_id,
      source_race_id: sourceId,
    });
    if (fromPy && fromPy.ok) {
      if (fromPy.provenanceMeta) {
        fromPy.provenanceMeta.canonical_race_id =
          fromPy.provenanceMeta.canonical_race_id || ref.canonical_race_id;
        fromPy.provenanceMeta.source_race_id =
          fromPy.provenanceMeta.source_race_id || sourceId;
        fromPy.provenanceMeta.core_race_id =
          fromPy.provenanceMeta.core_race_id || ref.core_race_id;
        if (idChanged) {
          fromPy.provenanceMeta.requested_race_id = raceId;
          fromPy.provenanceMeta.year_corrected = true;
        }
        // Infer race_type from authority when server omitted it
        if (!fromPy.provenanceMeta.race_type && fromPy.provenanceMeta.decision_authority) {
          fromPy.provenanceMeta.race_type =
            fromPy.provenanceMeta.decision_authority === "RESTORED_V2"
              ? "NORMAL"
              : fromPy.provenanceMeta.decision_authority === "CURRENT_PATH"
                ? "UNKNOWN_OR_MAIDEN"
                : null;
        }
      }
      return guardReadyOrPending(fromPy, predictId);
    }
    if (fromPy && fromPy.errorResponse) return fromPy;

    // Explicit diagnostic PI fallback only (never silent authority)
    if (env.PREDICTION_ALLOW_PI_FALLBACK && usePiProxy(env)) {
      const fromPi = await fetchFromPiGet(context, sourceId, null, {
        timeoutMs: predictionTimeoutMs(env),
      });
      if (fromPi && fromPi.ok) {
        if (fromPi.provenanceMeta) {
          fromPi.provenanceMeta.fallback_state = "explicit_pi_prediction_fallback";
          fromPi.provenanceMeta.fallback_reason = "ai_unavailable_pi_fallback";
          fromPi.provenanceMeta.decision_authority =
            fromPi.provenanceMeta.decision_authority || "CURRENT_PATH";
          fromPi.provenanceMeta.source_race_id = sourceId;
          fromPi.provenanceMeta.canonical_race_id = ref.canonical_race_id || null;
        }
        return guardReadyOrPending(fromPi, sourceId);
      }
    }

    return {
      ok: false,
      error: "Prediction unavailable from :8000 Bundle authority",
      status: 502,
      provenanceMeta: {
        engine: "n/a",
        engine_source: "real_ai",
        fallback_state: "ai_prediction_unavailable",
        canonical_race_id: ref.canonical_race_id || null,
        source_race_id: sourceId,
      },
    };
  }

  // AI not configured — legacy PI / mock for local-only
  if (usePiProxy(env)) {
    const fromPi = await fetchFromPiGet(context, sourceId);
    if (fromPi && fromPi.ok) {
      if (fromPi.provenanceMeta) {
        fromPi.provenanceMeta.fallback_state = "pi_only_no_ai_base_url";
        fromPi.provenanceMeta.decision_authority =
          fromPi.provenanceMeta.decision_authority || "CURRENT_PATH";
      }
      return guardReadyOrPending(fromPi, sourceId);
    }
    return pendingPredictionResult({
      raceId: sourceId,
      reason: fromPi?.error || "pi_prediction_unavailable",
      requestedRaceId: idChanged ? raceId : undefined,
      yearCorrected: idChanged || undefined,
      piError: fromPi?.error || "pi_failed",
    });
  }
  return guardReadyOrPending(await fetchFromMockGet(context, sourceId), sourceId);
}

export const PredictionAdapter = {
  list: adaptPredictionList,
  get: adaptPredictionGet,
  mergeListProvenanceMeta,
  mergeGetProvenanceMeta,
  _sources: {
    fetchFromPiList,
    fetchFromPiGet,
    fetchFromPythonList,
    fetchFromMockList,
    fetchFromPythonGet,
    fetchFromMockGet,
  },
};
