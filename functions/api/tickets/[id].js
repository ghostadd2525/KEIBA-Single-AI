import { aiFetch, loadAssetJson } from "../../_lib/aiProxy.js";
import { normalizePredictionBundle, projectTickets } from "../../_lib/domain.js";
import { jsonError, jsonOk } from "../../_lib/errors.js";

/**
 * TicketService — GET /api/tickets/:raceId
 * PredictionBundle.race_id をキーに、同 Bundle の betting_recommendations を投影
 */
export async function onRequestGet(context) {
  const id = context.params.id;
  if (!id) return jsonError("BAD_REQUEST", "race_id required", 400);

  const proxied = await aiFetch(context, `/v1/tickets/${encodeURIComponent(id)}`);
  if (proxied && proxied instanceof Response) return proxied;
  if (proxied && proxied.ok) {
    const data = proxied.payload.data != null ? proxied.payload.data : proxied.payload;
    return jsonOk(data, {
      source: "win5-ai",
      service: "TicketService",
      race_id: id,
    }, { cacheControl: "public, max-age=120" });
  }

  let bundle = await loadAssetJson(context, `/data/mocks/bundle-${id}.json`);
  if (!bundle) {
    bundle = await loadAssetJson(context, "/data/mocks/bundle-20260719_hanshin_11.json");
  }
  if (!bundle) return jsonError("NOT_FOUND", "PredictionBundle not found for race_id", 404);

  return jsonOk(projectTickets(normalizePredictionBundle(bundle, id)), {
    source: "mock",
    service: "TicketService",
    race_id: id,
    contract_ref: "PredictionBundle.betting_recommendations",
  }, { cacheControl: "public, max-age=120" });
}
