/**
 * GET /api/races/:id/odds-series
 * PI GET /v1/races/{id}/odds-series（単勝オッズ時系列）
 * ?refresh=1 でキャッシュ期限に合わせて再取得（TTL 内は netkeiba 非アクセス）
 */
import { piFetch } from "../../../_lib/piProxy.js";
import { isPiRaceId } from "../../../_lib/raceIdResolve.js";
import { jsonError, jsonOk } from "../../../_lib/errors.js";

export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);
  if (!isPiRaceId(id)) {
    return jsonError("INVALID_RACE_ID", "race_id must be YYYY-MM-DD-LL-RR", 400);
  }

  const url = new URL(context.request.url);
  const refresh = ["1", "true", "yes"].includes(
    String(url.searchParams.get("refresh") || "").toLowerCase()
  );
  const qs = refresh ? "?refresh=1" : "";
  const proxied = await piFetch(
    context,
    "/v1/races/" + encodeURIComponent(id) + "/odds-series" + qs,
    { timeoutMs: 45000 }
  );
  if (proxied instanceof Response) return proxied;
  if (!proxied || !proxied.ok || !proxied.payload) {
    return jsonError("PI_ODDS_SERIES_FAILED", "Failed to load odds series from PI API", 502);
  }

  const p = proxied.payload;
  return jsonOk(
    {
      schema_version: p.schema_version || "expect-odds-series/1.0",
      race_id: String(p.race_id || id),
      race_label: p.race_label || "",
      race_name: p.race_name || "",
      date: p.date || "",
      venue: p.venue || "",
      race_no: p.race_no != null ? Number(p.race_no) : null,
      post_time: p.post_time || null,
      numeric_race_id: p.numeric_race_id != null ? String(p.numeric_race_id) : null,
      sample_interval_sec: p.sample_interval_sec != null ? Number(p.sample_interval_sec) : 300,
      point_count: p.point_count != null ? Number(p.point_count) : 0,
      timestamps: Array.isArray(p.timestamps) ? p.timestamps : [],
      series: Array.isArray(p.series) ? p.series : [],
    },
    {
      source: proxied.source || "pi-keibanet-api",
      service: "OddsSeries",
    },
    {
      cacheControl: "private, max-age=30",
    }
  );
}
