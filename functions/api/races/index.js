/**
 * GET /api/races?date=YYYY-MM-DD
 *
 * PI KeibaNet API GET /v1/races をプロキシ（レスポンス本体は PI 形式のまま）。
 */
import { piFetch } from "../../_lib/piProxy.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestGet(context) {
  const url = new URL(context.request.url);
  const date = (url.searchParams.get("date") || "").trim();
  if (!date) {
    return jsonError("DATE_REQUIRED", "date query parameter is required (YYYY-MM-DD)", 400);
  }

  const qs = new URLSearchParams({ date });
  const proxied = await piFetch(context, "/v1/races?" + qs.toString());
  if (proxied instanceof Response) return proxied;
  if (!proxied || !proxied.ok) {
    return jsonError("PI_RACES_FAILED", "Failed to load race catalog from PI API", 502);
  }

  return jsonOk(proxied.payload, {
    source: proxied.source || "pi-keibanet-api",
    service: "RaceCatalog",
    cache: "public, max-age=60",
  });
}
