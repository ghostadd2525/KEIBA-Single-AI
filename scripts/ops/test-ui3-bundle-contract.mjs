/**
 * UI3 — ExpectContractGuard compatibility checks for mapper + domain ensure.
 * Run: node scripts/ops/test-ui3-bundle-contract.mjs
 */
import { mapSingleToPredictionBundle } from "../../functions/_lib/singleToBundleMapper.js";
import {
  ensurePredictionBundleContract,
  normalizePredictionBundle,
} from "../../functions/_lib/domain.js";

function assert(cond, msg) {
  if (!cond) throw new Error(msg || "assertion failed");
}

/** Mirror of public/assets/api/contract-guard.js validatePredictionBundle */
function validatePredictionBundle(bundle) {
  const errors = [];
  const PB_VERSION = "single-prediction-bundle/2.0";
  const isObj = (v) => v != null && typeof v === "object" && !Array.isArray(v);
  if (!isObj(bundle)) return { ok: false, errors: ["$: not an object"] };
  if (bundle.schema_version !== PB_VERSION) errors.push("schema_version");
  if (typeof bundle.race_id !== "string" || !bundle.race_id) errors.push("race_id");
  if (!isObj(bundle.race_info)) errors.push("race_info");
  else {
    if (typeof bundle.race_info.venue !== "string") errors.push("venue");
    if (typeof bundle.race_info.date !== "string") errors.push("date");
    if (typeof bundle.race_info.race_no !== "number") errors.push("race_no");
  }
  if (!isObj(bundle.evaluation) || !Array.isArray(bundle.evaluation.runners)) {
    errors.push("evaluation.runners");
  }
  if (!isObj(bundle.ai_confidence) || !("score" in bundle.ai_confidence)) {
    errors.push("ai_confidence.score");
  } else if (
    bundle.ai_confidence.score != null &&
    typeof bundle.ai_confidence.score !== "number"
  ) {
    errors.push("score type");
  }
  if (!isObj(bundle.explain) || typeof bundle.explain.narrative !== "string") {
    errors.push("explain.narrative");
  }
  if (
    !isObj(bundle.betting_recommendations) ||
    !Array.isArray(bundle.betting_recommendations.items)
  ) {
    errors.push("betting_recommendations.items");
  }
  return { ok: errors.length === 0, errors };
}

// 1) Mapper without base (previously missing narrative)
const mapped = mapSingleToPredictionBundle({
  core_payload: {
    race_id: "2026-07-19-04-11",
    prediction: { ranks: [5, 3], scores: [0.3, 0.2] },
  },
  race_id: "2026-07-19-04-11",
});
let r = validatePredictionBundle(mapped);
assert(r.ok, "mapper bare: " + r.errors.join(","));

// 2) Bad race_info overlay (string race_no, null venue)
const mapped2 = mapSingleToPredictionBundle(
  {
    core_payload: {
      race_id: "2026-07-19-04-11",
      prediction: { ranks: [1], scores: [0.5] },
    },
  },
  {
    race_id: "2026-07-19-04-11",
    race_info: { venue: null, date: null, race_no: "11" },
  }
);
r = validatePredictionBundle(mapped2);
assert(r.ok, "mapper coerce: " + r.errors.join(","));
assert(mapped2.race_info.race_no === 11, "race_no coerced");
assert(typeof mapped2.race_info.venue === "string", "venue string");

// 3) normalizePredictionBundle with null race_no
const norm = normalizePredictionBundle(
  {
    schema_version: "single-prediction-bundle/2.0",
    race_id: "2026-07-26-01-11",
    race_info: { venue: "新潟", date: "2026-07-26", race_no: null },
    evaluation: { runners: [] },
    ai_confidence: { score: null },
    explain: { reasons: [] },
    betting_recommendations: { schema_version: "x" },
  },
  "2026-07-26-01-11"
);
r = validatePredictionBundle(norm);
assert(r.ok, "normalize: " + r.errors.join(","));
assert(typeof norm.explain.narrative === "string", "narrative");
assert(Array.isArray(norm.betting_recommendations.items), "bets items");

// 4) ensure alone
const ens = ensurePredictionBundleContract({
  race_id: "x",
  race_info: {},
  evaluation: {},
  ai_confidence: {},
  explain: {},
});
r = validatePredictionBundle(ens);
assert(r.ok, "ensure: " + r.errors.join(","));

console.log("PASS ui3-bundle-contract", {
  mapped_narrative: mapped.explain.narrative,
  mapped2_race_no: mapped2.race_info.race_no,
  norm_race_no: norm.race_info.race_no,
});
