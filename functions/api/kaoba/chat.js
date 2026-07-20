/**
 * KaobaService — POST /api/kaoba/chat
 *
 * 応答生成は KaobaAdapter.chat のみ（rule / python）。
 * 契約・パス・画面は不変。
 */
import { KaobaAdapter } from "../../_lib/adapters/kaobaAdapter.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

export async function onRequestPost(context) {
  let body;
  try {
    body = await context.request.json();
  } catch {
    return jsonError("BAD_REQUEST", "JSON body required", 400);
  }

  const message = String((body && body.message) || "").trim();
  if (!message) {
    return jsonError("BAD_REQUEST", "message is required", 400);
  }

  const result = await KaobaAdapter.chat(context, body);
  if (result.errorResponse) return result.errorResponse;

  const raceId = result.response && result.response.referenced_race_id;

  return jsonOk(result.response, {
    source: result.source,
    service: "KaobaService",
    contract: "KaobaChatResponse",
    race_id: raceId,
    contract_ref: raceId ? "PredictionBundle.race_id" : null,
    cache: "bypass",
    provider: result.provider,
    adapter: "KaobaAdapter",
  }, { cacheControl: "no-store" });
}
