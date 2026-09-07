/**
 * GET /api/v1/stats/heatmap?venues=新潟,東京（任意・通常は全会場）
 * AI総合実績ヒートマップ — race_evaluations 全期間累積（リセットなし）
 * 静的285Rフォールバックは使わない（総合実績を偽らないため）
 */
import { aiFetch } from "../../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../../_lib/env.js";
import { jsonOk } from "../../../_lib/errors.js";
import {
  HEATMAP_SCHEMA,
  buildHeatmapPayload,
} from "../../../_lib/heatmapStats.js";

function emptyAllTimePayload() {
  return buildHeatmapPayload({
    schema_version: "expect-segment-hit-rates/1.0",
    corpus: "stats_db_all_time",
    overall_hit_rate: 0,
    overall_hits: 0,
    races_evaluated: 0,
    min_samples: 1,
    segments: {},
    segments_going: {},
    source: "stats_db",
    scope: "all_time_cumulative",
    resets: false,
    formula: "hit_at_1_count / ai_evaluated_race_count",
    label: "AI総合実績",
    generated_at: new Date().toISOString(),
  });
}

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
      return jsonOk(data, {
        ...(proxied.payload.meta || {}),
        source: proxied.payload.data?.source || "stats_db",
        scope: "all_time_cumulative",
        cache: "public, max-age=30",
      }, { cacheControl: "public, max-age=30" });
    }
  }

  // AI未接続時も空の総合実績を返す（デモ285Rは出さない）
  return jsonOk(emptyAllTimePayload(), {
    source: "empty-all-time",
    scope: "all_time_cumulative",
    cache: "public, max-age=30",
  }, { cacheControl: "public, max-age=30" });
}
