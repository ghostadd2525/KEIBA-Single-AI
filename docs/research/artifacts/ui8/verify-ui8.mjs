/**
 * UI8 client-side mapping smoke（prediction-bind と同等ロジック）
 */
import assert from "node:assert/strict";
import {
  confidenceBandFromLabelAndScore,
  resolveConfidenceDisplay,
  resolveInternalLabel,
  BAND_RANK,
} from "../../../../functions/_lib/confidenceBands.js";

function pickHomeTodaysHonmei(items) {
  const eligible = items.filter(
    (b) => (BAND_RANK[b.band] || 0) >= BAND_RANK.rather_high
  );
  if (!eligible.length) return null;
  return eligible.slice().sort((a, b) => b.score - a.score)[0];
}

const cases = [
  { world: "core_world", score: 0.8, band: "high", stars: "★★★★★" },
  { world: "midupper_world", score: 0.8, band: "rather_high", stars: "★★★★☆" },
  { world: "midhole_world", score: 0.9, band: "medium", stars: "★★★☆☆" },
  { world: "unsatisfied", score: 0.99, band: "low", stars: "★★☆☆☆" },
  { world: "turf", score: 0.5, band: "medium", stars: "★★★☆☆" },
];

for (const c of cases) {
  const { label, band } = resolveConfidenceDisplay({
    world: c.world,
    score: c.score,
  });
  assert.equal(band, c.band, `${c.world} → ${band}`);
  assert.ok(label);
}

const pick = pickHomeTodaysHonmei([
  { id: "a", band: "medium", score: 0.9 },
  { id: "b", band: "rather_high", score: 0.62 },
  { id: "c", band: "high", score: 0.7 },
]);
assert.equal(pick.id, "c");

const none = pickHomeTodaysHonmei([
  { id: "a", band: "medium", score: 0.9 },
  { id: "b", band: "low", score: 0.2 },
]);
assert.equal(none, null);

assert.equal(resolveInternalLabel({ world: "midupper_world", score: 0.1 }), "near_miss");
assert.equal(confidenceBandFromLabelAndScore("near_miss", 0.1), "low");

console.log("ui8-verify PASS", cases.length, "mapping + home pick");
