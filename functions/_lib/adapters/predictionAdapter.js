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
import { findPiRaceInCatalog } from "../raceIdResolve.js";

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

async function fetchFromPiGet(context, raceId, catalogRace = null) {
  const proxied = await piFetch(
    context,
    `/v1/predictions/${encodeURIComponent(raceId)}`
  );
  if (proxied instanceof Response) {
    return { ok: false, errorResponse: proxied };
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
  const bundle = mapPiPredictionToBundle(payload, row);
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
  for (const race of races) {
    const rid = String(race.race_id || "");
    if (!rid) continue;
    const one = await fetchFromPiGet(context, rid, race);
    if (one && one.ok) {
      bundles.push(one.bundle);
      items.push(
        piProvenanceItem(rid, one.bundle, {
          numeric_race_id: race.numeric_race_id || null,
        })
      );
    }
  }

  if (!bundles.length) {
    return { ok: false, error: "No PI predictions available for date", status: 404 };
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
  const proxied = await aiFetch(context, `/v1/predictions/${encodeURIComponent(raceId)}`);
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

/** 1件: PI →（未設定時）Python AI →（未設定時）bff_mock */
export async function adaptPredictionGet(context, raceId) {
  const env = getEnv(context);
  if (usePiProxy(env)) {
    const fromPi = await fetchFromPiGet(context, raceId);
    if (fromPi && fromPi.ok) return fromPi;
    if (fromPi && fromPi.errorResponse) return fromPi;
    return {
      ok: false,
      error: fromPi?.error || "Prediction not found",
      status: fromPi?.status || 404,
    };
  }
  if (useAiProxy(env)) {
    const fromPy = await fetchFromPythonGet(context, raceId);
    if (fromPy && fromPy.ok) return fromPy;
    if (fromPy && fromPy.errorResponse) return fromPy;
    return { ok: false, error: "Prediction unavailable", status: 502 };
  }
  return fetchFromMockGet(context, raceId);
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
