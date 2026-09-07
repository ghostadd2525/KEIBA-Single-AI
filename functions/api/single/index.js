/**
 * I1 — POST /api/single
 * Body: { race_id, core_payload, options?, force?, timeout_ms? }
 *
 * Same-origin for existing site. Does not replace /api/predictions.
 */
import { SingleSiteAdapter } from "../../_lib/adapters/singleSiteAdapter.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestPost(context) {
  let body;
  try {
    body = await context.request.json();
  } catch {
    return jsonError("BAD_REQUEST", "JSON body required", 400);
  }
  if (!body || typeof body !== "object") {
    return jsonError("BAD_REQUEST", "JSON object required", 400);
  }

  const result = await SingleSiteAdapter.call(context, body);
  if (!result.ok) {
    if (result.errorResponse) return result.errorResponse;
    return jsonError(
      result.code || "AI_ERROR",
      result.error || "Single Site call failed",
      result.status || 502,
      result.details || null
    );
  }

  const payload = result.payload || {};
  if (payload.ok === false && payload.error) {
    return jsonError(
      payload.error.code || "AI_ERROR",
      payload.error.message || "error",
      502,
      payload.error.details || null
    );
  }

  const data = payload.data != null ? payload.data : payload;
  return jsonOk(data, {
    ...(payload.meta || {}),
    service: "SingleSiteIntegration",
    adapter: "SingleSiteAdapter",
    source: result.source,
    race_id: result.race_id,
  });
}
