/**
 * UI1 — POST /api/ui/prediction-bundle
 * Maps Single/core → PredictionBundle for existing UI (layout unchanged).
 */
import { aiFetch } from "../../_lib/aiProxy.js";
import { getEnv, useAiProxy } from "../../_lib/env.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";
import { mapSingleToPredictionBundle } from "../../_lib/singleToBundleMapper.js";

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

  const env = getEnv(context);
  // Prefer Python mapper when AI is available (single source of truth)
  if (useAiProxy(env)) {
    const proxied = await aiFetch(context, "/v1/ui/prediction-bundle", {
      method: "POST",
      body: JSON.stringify(body),
      timeoutMs: 12000,
    });
    if (!(proxied instanceof Response) && proxied && proxied.ok) {
      const payload = proxied.payload || {};
      const data = payload.data != null ? payload.data : payload;
      return jsonOk(data, {
        ...(payload.meta || {}),
        service: "UiAdaptation",
        adapter: "singleToBundleMapper",
        source: "win5-ai",
        layout_changed: false,
      });
    }
    // fall through to local mapper on soft failure
  }

  try {
    const source =
      body.single_response ||
      body.single ||
      (body.core_payload
        ? { core_payload: body.core_payload, race_id: body.race_id }
        : body);
    const bundle = mapSingleToPredictionBundle(source, {
      race_id: body.race_id,
      race_info: body.race_info,
      base_bundle: body.base_bundle,
    });
    return jsonOk(bundle, {
      service: "UiAdaptation",
      adapter: "singleToBundleMapper",
      source: "bff-local",
      layout_changed: false,
      internal_terms_exposed: false,
    });
  } catch (e) {
    return jsonError("MAP_ERROR", String(e && e.message ? e.message : e), 500);
  }
}
