/**
 * 285R 評価結果から会場×芝ダ×距離の◎的中率を集計し、
 * fixtures/stats/segment-hit-rates.json と functions/_lib/segmentHitRates.js を更新する。
 *
 * 入力（任意）:
 *   --eval-json path/to/eval-rows.json  [{ venue, surface, distance, hit_at_1 }, ...]
 */
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  MODEL_WEIGHT,
  SEGMENT_WEIGHT,
  MIN_SEGMENT_SAMPLES,
  segmentKey,
  surfaceJa,
  distanceBucket,
} from "../../functions/_lib/segmentConfidence.js";
import { normalizeGoing } from "../../functions/_lib/heatmapStats.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, "../..");

function parseArgs(argv) {
  const out = { evalJson: null };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === "--eval-json" && argv[i + 1]) {
      out.evalJson = argv[++i];
    }
  }
  return out;
}

function aggregate(rows) {
  const segments = {};
  const segmentsGoing = {};
  let hits = 0;
  let total = 0;
  for (const row of rows) {
    if (!row || row.hit_at_1 == null) continue;
    total += 1;
    if (row.hit_at_1) hits += 1;
    const venue = String(row.venue || "").trim();
    if (!venue) continue;
    const surf = surfaceJa(row.surface);
    const key = segmentKey(venue, surf, distanceBucket(row.distance));
    if (!segments[key]) segments[key] = { hits: 0, n: 0 };
    segments[key].n += 1;
    if (row.hit_at_1) segments[key].hits += 1;
    const going = normalizeGoing(row.going);
    if (going) {
      const gKey = `${venue}|${surf}|${going}`;
      if (!segmentsGoing[gKey]) segmentsGoing[gKey] = { hits: 0, n: 0 };
      segmentsGoing[gKey].n += 1;
      if (row.hit_at_1) segmentsGoing[gKey].hits += 1;
    }
  }
  const segmentOut = {};
  for (const [key, val] of Object.entries(segments)) {
    segmentOut[key] = {
      hit_rate: Math.round((val.hits / val.n) * 10000) / 10000,
      n: val.n,
    };
  }
  const goingOut = {};
  for (const [key, val] of Object.entries(segmentsGoing)) {
    goingOut[key] = {
      hit_rate: Math.round((val.hits / val.n) * 10000) / 10000,
      n: val.n,
    };
  }
  return {
    overall_hit_rate: total ? Math.round((hits / total) * 10000) / 10000 : 218 / 285,
    segments: segmentOut,
    segments_going: goingOut,
    races_evaluated: total,
  };
}

function toJsModule(data) {
  return `/**
 * 会場×芝ダ×距離の◎的中率（${data.corpus} コーパス由来）
 * 更新: node scripts/ops/build-segment-hit-rates.mjs
 */
export const SEGMENT_HIT_RATES = ${JSON.stringify(data, null, 2)};
`;
}

function main() {
  const args = parseArgs(process.argv);
  let rows = [];
  if (args.evalJson) {
    rows = JSON.parse(readFileSync(args.evalJson, "utf8"));
  }

  const agg = aggregate(rows);
  const payload = {
    schema_version: "expect-segment-hit-rates/1.0",
    corpus: rows.length ? "eval-import" : "285R",
    generated_at: new Date().toISOString(),
    overall_hit_rate: agg.overall_hit_rate,
    min_samples: MIN_SEGMENT_SAMPLES,
    blend: { model_weight: MODEL_WEIGHT, segment_weight: SEGMENT_WEIGHT },
    segments: agg.segments,
    segments_going: agg.segments_going,
    races_evaluated: agg.races_evaluated,
  };

  const jsonPath = join(ROOT, "fixtures/stats/segment-hit-rates.json");
  const jsPath = join(ROOT, "functions/_lib/segmentHitRates.js");
  writeFileSync(jsonPath, JSON.stringify(payload, null, 2) + "\n", "utf8");
  writeFileSync(jsPath, toJsModule(payload), "utf8");
  console.log(`Wrote ${jsonPath}`);
  console.log(`Wrote ${jsPath}`);
  console.log(
    `overall=${payload.overall_hit_rate} segments=${Object.keys(payload.segments).length}`
  );
}

main();
