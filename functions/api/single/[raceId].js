/**
 * I1 — POST /api/single/:raceId
 * Path race_id + body.core_payload (and optional body fields).
 */
import { SingleSiteAdapter } from "../../_lib/adapters/singleSiteAdapter.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { normalizeRaceIdYear } from "../../_lib/raceIdYear.js";

export async function onRequestPost(context) {
  const raceId = normalizeRaceIdYear(String(context.params.raceId || "").trim());
  if (!raceId) return jsonError("BAD_RACE_ID", "race_id required", 400);

  let body;
  try {
    body = await context.request.json();
  } catch {
    return jsonError("BAD_REQUEST", "JSON body required", 400);
  }
  if (!body || typeof body !== "object") {
    return jsonError("BAD_REQUEST", "JSON object required", 400);
  }

  const result = await SingleSiteAdapter.call(context, {
    ...body,
    race_id: raceId,
  });
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
    const status =
      payload.error.code === "TIMEOUT"
        ? 504
        : payload.error.code === "CONSUMER_DISABLED" ||
            payload.error.code === "SERVICE_DISABLED"
          ? 503
          : payload.error.code === "UNAUTHORIZED"
            ? 401
            : 400;
    return jsonError(
      payload.error.code || "AI_ERROR",
      payload.error.message || "error",
      status,
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
