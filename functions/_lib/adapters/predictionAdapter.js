/**
 * PredictionAdapter — PredictionBundle 取得の差し替え点
 *
 * 契約（single-prediction-bundle/2.0）・HTTP API は変更しない。
 * V1.1: PI_BASE_URL 設定時は PI /v1/predictions を正とし mock_fallback しない。
 * 開発のみ: PI/AI 未設定時は ASSETS mock（bff_mock）。
 */
import { aiFetch, loadAssetJson } from "../aiProxy.js";
import { catalogToPredictionBundle, normalizePredictionBundle } from "../domain.js";
import { getEnv, useAiProxy } from "../env.js";
import { mapPiPredictionToBundle, piProvenanceItem } from "../piPredictionMapper.js";
import { piFetch, usePiProxy } from "../piProxy.js";
import {
  isReadyPredictionBundle,
  warnProjectionSuppressed,
} from "../predictionReady.js";
import { findPiRaceInCatalog } from "../raceIdResolve.js";
import { normalizeRaceIdYear } from "../raceIdYear.js";

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

/** 成功応答のガード: 空 runners / projection は pending に落とす */
function guardReadyOrPending(result, raceId) {
  if (!result || !result.ok) return result;
  const meta = result.provenanceMeta || {};
  if (isReadyPredictionBundle(result.bundle, meta)) return result;
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
  if (provenanceMeta.race_id) next.race_id = provenanceMeta.race_id;
  if (provenanceMeta.core_race_id) next.core_race_id = provenanceMeta.core_race_id;
  if (provenanceMeta.numeric_race_id) next.numeric_race_id = provenanceMeta.numeric_race_id;
  if (provenanceMeta.feature_source) next.feature_source = provenanceMeta.feature_source;
  if (provenanceMeta.fallback_reason) next.fallback_reason = provenanceMeta.fallback_reason;
  if (provenanceMeta.detail) next.detail = provenanceMeta.detail;
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

async function fetchFromPythonGet(context, raceId) {
  const proxied = await aiFetch(context, `/v1/predictions/${encodeURIComponent(raceId)}`, {
    timeoutMs: 10000,
  });
  if (proxied && proxied instanceof Response) {
    return { ok: false, errorResponse: proxied };
  }
  if (!proxied || !proxied.ok) return null;
  const data = proxied.payload.data != null ? proxied.payload.data : proxied.payload;
  const meta = proxied.payload.meta || {};
  return {
    ok: true,
    bundle: normalizePredictionBundle(data, raceId),
    source: "single-ai",
    provider: "python",
    provenanceMeta: {
      ...meta,
      engine: meta.engine || "real",
      engine_source: normalizeEngineSource(meta.engine_source || "real"),
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

/** 一覧: PI →（未設定時）Python AI →（未設定時）bff_mock */
export async function adaptPredictionList(context, query = {}) {
  const env = getEnv(context);
  if (usePiProxy(env)) {
    return fetchFromPiList(context, query);
  }
  if (useAiProxy(env)) {
    const fromPy = await fetchFromPythonList(context, query);
    if (fromPy && fromPy.ok) return fromPy;
    if (fromPy && fromPy.errorResponse) return fromPy;
    return { ok: false, error: "Prediction list unavailable", status: 502 };
  }
  return fetchFromMockList(context, query);
}

/** 1件: PI →（失敗/タイムアウト時）Python AI → カタログ投影 →（未設定時）bff_mock */
export async function adaptPredictionGet(context, raceId) {
  const env = getEnv(context);
  const normalizedId = normalizeRaceIdYear(raceId);
  const idChanged = normalizedId && normalizedId !== String(raceId || "").trim();

  if (usePiProxy(env)) {
    const fromPi = await fetchFromPiGet(context, normalizedId);
    if (fromPi && fromPi.ok) {
      if (idChanged && fromPi.provenanceMeta) {
        fromPi.provenanceMeta.requested_race_id = raceId;
        fromPi.provenanceMeta.race_id = normalizedId;
        fromPi.provenanceMeta.year_corrected = true;
      }
      return guardReadyOrPending(fromPi, normalizedId);
    }

    // PI 不通・タイムアウト時のみ AI へフェイルオーバー（同一オリジンならスキップ）
    const sameOriginFailover =
      env.AI_BASE_URL &&
      env.PI_BASE_URL &&
      String(env.AI_BASE_URL).replace(/\/$/, "") === String(env.PI_BASE_URL).replace(/\/$/, "");
    if (useAiProxy(env) && !sameOriginFailover) {
      const fromPy = await fetchFromPythonGet(context, normalizedId);
      if (fromPy && fromPy.ok) {
        if (fromPy.provenanceMeta) {
          fromPy.provenanceMeta.fallback_reason = "pi_unavailable_ai_failover";
          fromPy.provenanceMeta.pi_error = fromPi?.error || "pi_failed";
          if (idChanged) {
            fromPy.provenanceMeta.requested_race_id = raceId;
            fromPy.provenanceMeta.year_corrected = true;
          }
        }
        return guardReadyOrPending(fromPy, normalizedId);
      }
    }

    // 旧: カタログ空 Projection を HTTP200 成功で返していた → pending に変更
    // （ヘッダー用メタはクライアントの race_list_cache / prefetch meta が担う）
    let numericFromCatalog = null;
    const m = String(normalizedId || "").match(/^(\d{4}-\d{2}-\d{2})/);
    if (m) {
      try {
        const catalogProxied = await piFetch(
          context,
          `/v1/races?date=${encodeURIComponent(m[1])}`,
          { timeoutMs: 6000 }
        );
        if (catalogProxied && !(catalogProxied instanceof Response) && catalogProxied.ok) {
          const races = Array.isArray(catalogProxied.payload.races)
            ? catalogProxied.payload.races
            : [];
          const row = races.find((r) => String(r.race_id || "") === String(normalizedId));
          if (row && row.numeric_race_id) numericFromCatalog = row.numeric_race_id;
        }
      } catch {
        /* ignore catalog lookup */
      }
    }

    return pendingPredictionResult({
      raceId: normalizedId,
      numericRaceId: numericFromCatalog,
      reason: fromPi?.error || "pi_prediction_unavailable",
      requestedRaceId: idChanged ? raceId : undefined,
      yearCorrected: idChanged || undefined,
      piError: fromPi?.error || "pi_failed",
    });
  }
  if (useAiProxy(env)) {
    const fromPy = await fetchFromPythonGet(context, normalizedId);
    if (fromPy && fromPy.ok) return guardReadyOrPending(fromPy, normalizedId);
    if (fromPy && fromPy.errorResponse) return fromPy;
    return { ok: false, error: "Prediction unavailable", status: 502 };
  }
  return guardReadyOrPending(await fetchFromMockGet(context, normalizedId), normalizedId);
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
