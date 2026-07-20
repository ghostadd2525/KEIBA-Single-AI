/**
 * PredictionAdapter — PredictionBundle 取得の差し替え点
 *
 * 契約（single-prediction-bundle/2.0）・HTTP API は変更しない。
 * 内部ソースのみ: python（AI_BASE_URL）→ mock（ASSETS）
 *
 * Phase7-08: Python envelope meta（provenance）を BFF meta へマージする。
 * PB 本体には provider / engine_source を載せない。
 */
import { aiFetch, loadAssetJson } from "../aiProxy.js";
import { catalogToPredictionBundle, normalizePredictionBundle } from "../domain.js";

/**
 * @typedef {{
 *   ok: true,
 *   bundles: object[],
 *   source: string,
 *   provider: string,
 *   provenanceMeta: object
 * } | { ok: false, errorResponse: Response }
 *   | { ok: false, error: string, status?: number }} ListResult
 */

/**
 * @typedef {{
 *   ok: true,
 *   bundle: object,
 *   source: string,
 *   provider: string,
 *   provenanceMeta: object
 * } | { ok: false, errorResponse: Response }
 *   | { ok: false, error: string, status?: number }} GetResult
 */

function bffMockItem(bundle) {
  return {
    race_id: bundle.race_id,
    engine_source: "bff_mock",
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
  return next;
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
  const items = Array.isArray(raw) ? raw : raw.items || [];
  return {
    ok: true,
    bundles: items.map((b) => normalizePredictionBundle(b, b.race_id)),
    source: "single-ai",
    provider: "python",
    provenanceMeta: proxied.payload.meta || {},
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
  return {
    ok: true,
    bundle: normalizePredictionBundle(data, raceId),
    source: "single-ai",
    provider: "python",
    provenanceMeta: proxied.payload.meta || {},
  };
}

async function fetchFromMockGet(context, raceId) {
  let bundle = await loadAssetJson(context, `/data/mocks/bundle-${raceId}.json`);
  if (!bundle) {
    bundle = await loadAssetJson(context, "/data/mocks/bundle-20260719_hanshin_11.json");
    if (!bundle) return { ok: false, error: "PredictionBundle not found", status: 404 };
  }
  const normalized = normalizePredictionBundle(bundle, raceId);
  const item = bffMockItem(normalized);
  return {
    ok: true,
    bundle: normalized,
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

/** 一覧: Python AI → Mock */
export async function adaptPredictionList(context, query = {}) {
  const fromPy = await fetchFromPythonList(context, query);
  if (fromPy) return fromPy;
  return fetchFromMockList(context, query);
}

/** 1件: Python AI → Mock */
export async function adaptPredictionGet(context, raceId) {
  const fromPy = await fetchFromPythonGet(context, raceId);
  if (fromPy) return fromPy;
  return fetchFromMockGet(context, raceId);
}

export const PredictionAdapter = {
  list: adaptPredictionList,
  get: adaptPredictionGet,
  mergeListProvenanceMeta,
  mergeGetProvenanceMeta,
  _sources: {
    fetchFromPythonList,
    fetchFromMockList,
    fetchFromPythonGet,
    fetchFromMockGet,
  },
};
