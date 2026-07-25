import test from "node:test";
import assert from "node:assert/strict";
import {
  HEATMAP_SCHEMA,
  buildHeatmapPayload,
  hitRateBand,
  hitRatePercent,
} from "../../functions/_lib/heatmapStats.js";

test("hitRateBand thresholds", () => {
  assert.equal(hitRateBand(0.65), "high");
  assert.equal(hitRateBand(0.4), "medium");
  assert.equal(hitRateBand(0.2), "low");
  assert.equal(hitRateBand(null), "unknown");
});

test("hitRatePercent normalizes ratio and percent", () => {
  assert.equal(hitRatePercent(0.765), 77);
  assert.equal(hitRatePercent(76.5), 77);
});

test("buildHeatmapPayload shapes distance and condition grids", () => {
  const table = {
    overall_hit_rate: 0.76,
    races_evaluated: 10,
    generated_at: "2026-07-22T08:00:00.000Z",
    segments: {
      "東京|芝|1600": { hit_rate: 0.8, n: 5 },
    },
    segments_going: {
      "東京|芝|良": { hit_rate: 0.75, n: 4 },
    },
  };
  const payload = buildHeatmapPayload(table, ["東京"]);
  assert.equal(payload.schema_version, HEATMAP_SCHEMA);
  assert.deepEqual(payload.distance.venues, ["東京"]);
  assert.equal(payload.distance.rows.length, 1);
  assert.equal(payload.distance.rows[0].cells[1].pct, 80);
  assert.equal(payload.condition.rows.length, 1);
  const row = payload.condition.rows[0];
  assert.equal(row.label, "東京");
  assert.equal(row.cells[0].pct, 75);
});

test("buildHeatmapPayload marks sparse cells as unknown", () => {
  const payload = buildHeatmapPayload(
    {
      overall_hit_rate: 0.76,
      segments: { "新潟|芝|1600": { hit_rate: 0.8, n: 5 } },
      segments_going: {},
    },
    ["新潟"]
  );
  assert.equal(payload.distance.rows[0].cells[0].band, "unknown");
  assert.equal(payload.distance.rows[0].cells[0].label, "—");
});
