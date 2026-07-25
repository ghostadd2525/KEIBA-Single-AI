/**
 * GET /api/v1/stats/heatmap?venues=新潟,東京
 * 過去◎的中率ヒートマップ（リアルタイム更新は AI stats DB → 静的 JSON フォールバック）
 */
import { aiFetch } from "../../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../../_lib/env.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";
import {
  HEATMAP_SCHEMA,
  buildHeatmapPayload,
} from "../../../_lib/heatmapStats.js";
import { SEGMENT_HIT_RATES } from "../../../_lib/segmentHitRates.js";

function normalizeHeatmapPayload(raw, venueFilter) {
  if (!raw) return null;
  if (
    raw.schema_version === HEATMAP_SCHEMA &&
    raw.distance &&
    raw.condition
  ) {
    return raw;
  }
  return buildHeatmapPayload(raw, venueFilter);
}

function parseVenueFilter(url) {
  const raw = (url.searchParams.get("venues") || "").trim();
  if (!raw) return null;
  return raw
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
}

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const venueFilter = parseVenueFilter(url);
  const env = getEnv(context);

  if (useAiProxy(env)) {
    const qs = venueFilter ? `?venues=${encodeURIComponent(venueFilter.join(","))}` : "";
    const proxied = await aiFetch(context, `/v1/stats/heatmap${qs}`);
    if (proxied && proxied instanceof Response) return proxied;
    if (proxied && proxied.ok && proxied.payload?.data) {
      const data = normalizeHeatmapPayload(proxied.payload.data, venueFilter);
      const hasRows =
        (data?.distance?.venues && data.distance.venues.length > 0) ||
        Number(data?.races_evaluated || 0) > 0;
      // stats_db が空のときは静的コーパスへフォールバック（ホーム空表示を防ぐ）
      if (hasRows) {
        return jsonOk(data, {
          ...(proxied.payload.meta || {}),
          source: proxied.payload.data?.source || "stats_db",
          cache: "public, max-age=30",
        }, { cacheControl: "public, max-age=30" });
      }
    }
  }

  const data = normalizeHeatmapPayload(
    { ...SEGMENT_HIT_RATES, source: "static-segments" },
    venueFilter
  );
  return jsonOk(data, { source: "static-segments", cache: "public, max-age=60" }, {
    cacheControl: "public, max-age=60",
  });
}
