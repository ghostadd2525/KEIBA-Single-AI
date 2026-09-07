/**
 * I1 — GET /api/single/version
 */
import { SingleSiteAdapter } from "../../_lib/adapters/singleSiteAdapter.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestGet(context) {
  const result = await SingleSiteAdapter.version(context);
  if (!result.ok) {
    if (result.errorResponse) return result.errorResponse;
    return jsonError(result.code || "AI_ERROR", result.error || "unavailable", result.status || 503);
  }
  const payload = result.payload || {};
  const data = payload.data != null ? payload.data : payload;
  return jsonOk(data, {
    service: "SingleSiteIntegration",
    adapter: "SingleSiteAdapter",
    api_version: "i1/1.0",
  });
}
