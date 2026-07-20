/**
 * AnalysisAdapter — Analysis DTO 取得の差し替え点
 *
 * 契約（expect-analysis/1.0）・GET /api/analysis/:id は変更しない。
 * キーは常に PredictionBundle.race_id。
 *
 * 実AI移行時: fetchFromPython の上流、または RealAiAnalysisSource を追加。
 */
import { aiFetch, loadAssetJson } from "../aiProxy.js";
import { toAnalysisDomain } from "../domain.js";

const DEFAULT_CHARTS = [
  { key: "pedigree", label: "血統", value: 70 },
  { key: "pace", label: "展開", value: 68 },
  { key: "jockey", label: "騎手", value: 66 },
  { key: "form", label: "近走", value: 67 },
  { key: "odds", label: "オッズ", value: 64 },
];

/** Python /v1/analysis → Analysis 契約形へ正規化 */
export function adaptAnalysisPayload(raw, raceId) {
  return toAnalysisDomain(raw, raceId);
}

async function fetchFromPython(context, raceId) {
  const proxied = await aiFetch(context, `/v1/analysis/${encodeURIComponent(raceId)}`);
  if (proxied && proxied instanceof Response) {
    return { ok: false, errorResponse: proxied };
  }
  if (!proxied || !proxied.ok) return null;
  const data = proxied.payload.data != null ? proxied.payload.data : proxied.payload;
  return {
    ok: true,
    analysis: adaptAnalysisPayload(data, raceId),
    source: "single-ai",
    provider: "python",
  };
}

async function fetchFromMock(context, raceId) {
  const all = await loadAssetJson(context, "/data/mocks/analysis.json");
  if (!all) return { ok: false, error: "analysis mock not found", status: 500 };
  const row = all[raceId] || {
    race_id: raceId,
    charts: DEFAULT_CHARTS,
    overall: 70,
    narrative: "データ準備中のレースです。",
  };
  return {
    ok: true,
    analysis: adaptAnalysisPayload(row, raceId),
    source: "mock",
    provider: "mock",
  };
}

/** Python AI → Mock */
export async function adaptAnalysisGet(context, raceId) {
  const fromPy = await fetchFromPython(context, raceId);
  if (fromPy) return fromPy;
  return fetchFromMock(context, raceId);
}

export const AnalysisAdapter = {
  get: adaptAnalysisGet,
  adaptPayload: adaptAnalysisPayload,
  _sources: { fetchFromPython, fetchFromMock },
};
