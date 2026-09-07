/**
 * Version8.1 — per-Miss multi Root Cause scoring (Research only).
 * Does not touch Prediction Engine / Candidate Evaluation / AI Core.
 *
 * Output shape (per race):
 *   root_cause_families: string[]   // multi allowed
 *   scores: Record<family, 0..1>
 *   confidence: Record<family, 0..1>
 */
export const FAMILY_IDS = Object.freeze([
  "candidate_pool",
  "repick",
  "delete",
  "purchase",
  "confidence",
  "world",
  "subworld",
  "ranking",
  "features",
  "ops_data",
  "unknown",
]);

/** Expected Hit impact weight for Priority (Research heuristic). */
export const IMPACT_WEIGHT = Object.freeze({
  candidate_pool: 1.0,
  repick: 0.85,
  delete: 0.7,
  purchase: 0.55,
  confidence: 0.6,
  world: 0.5,
  subworld: 0.45,
  ranking: 0.75,
  features: 0.4,
  ops_data: 0.2,
  unknown: 0.15,
});

const FAMILY_THRESHOLD = 0.18;

function horseNum(x) {
  if (x == null) return null;
  if (typeof x === "number" && Number.isFinite(x)) return x;
  if (typeof x === "object") {
    const n = x.horse_number ?? x.num ?? x.umaban ?? x.number;
    return n != null && Number.isFinite(Number(n)) ? Number(n) : null;
  }
  const n = Number(x);
  return Number.isFinite(n) ? n : null;
}

function asPool(payload) {
  const raw =
    payload.candidate_pool ||
    payload.candidates ||
    payload.marks ||
    payload.top_candidates ||
    [];
  if (!Array.isArray(raw)) return [];
  return raw.map(horseNum).filter((n) => n != null);
}

function asDeleted(payload) {
  const raw = payload.deleted || payload.delete_list || payload.exclusions || [];
  if (!Array.isArray(raw)) return [];
  return raw.map(horseNum).filter((n) => n != null);
}

function winnerNum(payload) {
  return (
    horseNum(payload.winner) ??
    horseNum(payload.winner_horse_number) ??
    horseNum(payload.result_winner) ??
    null
  );
}

function conf01(payload) {
  const c = payload.confidence;
  if (typeof c !== "number" || !Number.isFinite(c)) return null;
  // Production often uses 0..100; Research also accepts 0..1
  return c > 1 ? c / 100 : c;
}

function clamp01(x) {
  if (!Number.isFinite(x)) return 0;
  return Math.max(0, Math.min(1, Math.round(x * 1000) / 1000));
}

/**
 * Score a single Miss evidence payload → multi-family scores.
 * @param {object} payload
 * @param {{ race_id?: string|null }} [meta]
 */
export function scoreMissEvent(payload = {}, meta = {}) {
  const scores = Object.fromEntries(FAMILY_IDS.map((id) => [id, 0]));
  const cat = String(payload.miss_category || "unknown");
  const pool = asPool(payload);
  const deleted = asDeleted(payload);
  const winner = winnerNum(payload);
  const conf = conf01(payload);
  const signals = [];

  // Baseline from miss_category (multi-factor seed)
  if (cat === "miss_top1") {
    scores.repick += 0.45;
    scores.ranking += 0.4;
    scores.purchase += 0.12;
    signals.push("miss_top1→repick+ranking");
  } else if (cat === "miss_top3") {
    scores.repick += 0.35;
    scores.ranking += 0.35;
    scores.candidate_pool += 0.2;
    signals.push("miss_top3→repick+ranking+pool");
  } else if (cat === "miss_top5") {
    scores.candidate_pool += 0.5;
    scores.ranking += 0.25;
    scores.delete += 0.1;
    signals.push("miss_top5→candidate_pool");
  } else {
    scores.unknown += 0.3;
    signals.push("unknown_miss_category");
  }

  // Structural: pool vs winner
  if (winner != null) {
    if (pool.length === 0) {
      scores.candidate_pool += 0.45;
      signals.push("empty_candidate_pool");
    } else if (!pool.includes(winner)) {
      scores.candidate_pool += 0.55;
      scores.repick += 0.08;
      signals.push("winner_not_in_pool");
    } else {
      const idx = pool.indexOf(winner);
      scores.repick += idx === 0 ? 0.25 : 0.4;
      scores.ranking += idx === 0 ? 0.2 : 0.3;
      if (idx > 0) signals.push(`winner_in_pool_rank_${idx + 1}`);
      else signals.push("winner_was_top_of_pool_but_miss_top1");
    }
  }

  if (winner != null && deleted.includes(winner)) {
    scores.delete += 0.7;
    scores.candidate_pool += 0.1;
    signals.push("winner_in_delete_list");
  }

  if (conf != null && conf >= 0.8 && (cat === "miss_top1" || cat === "miss_top3")) {
    scores.confidence += 0.45;
    signals.push("high_confidence_miss");
  } else if (conf != null && conf >= 0.65) {
    scores.confidence += 0.2;
  }

  if (payload.world || payload.world_id) {
    scores.world += 0.25;
    signals.push("world_present");
  }
  if (payload.sub_world || payload.subworld || payload.sub_world_id) {
    scores.subworld += 0.25;
    signals.push("subworld_present");
  }
  if (payload.feature_missing || payload.feature_source === "missing") {
    scores.features += 0.5;
    signals.push("feature_missing_flag");
  }

  // Clamp raw then derive active families
  for (const id of FAMILY_IDS) scores[id] = clamp01(scores[id]);

  const families = Object.entries(scores)
    .filter(([, s]) => s >= FAMILY_THRESHOLD)
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id);

  if (!families.length) {
    families.push("unknown");
    scores.unknown = Math.max(scores.unknown, 0.25);
  }

  // Per-family confidence: score * signal richness, capped
  const richness = Math.min(1, 0.35 + signals.length * 0.08);
  const confidence = {};
  for (const id of FAMILY_IDS) {
    confidence[id] = scores[id] > 0 ? clamp01(scores[id] * (0.55 + 0.45 * richness)) : 0;
  }

  const primary = families[0];
  return {
    schema_version: "expect-root-cause-score/1.0",
    race_id: meta.race_id ?? payload.race_id ?? null,
    miss_category: cat === "unknown" ? null : cat,
    root_cause_families: families,
    scores,
    confidence,
    primary_family: primary,
    primary_score: scores[primary],
    signals,
  };
}

/**
 * Aggregate per-event scores across a Miss corpus.
 * @param {object[]} perRace
 */
export function aggregateScores(perRace) {
  const n = perRace.length || 0;
  const scores = Object.fromEntries(FAMILY_IDS.map((id) => [id, 0]));
  const confidence = Object.fromEntries(FAMILY_IDS.map((id) => [id, 0]));
  const freq = Object.fromEntries(FAMILY_IDS.map((id) => [id, 0]));

  if (!n) {
    return {
      event_count: 0,
      scores,
      confidence,
      frequency: freq,
      frequency_pct: Object.fromEntries(FAMILY_IDS.map((id) => [id, 0])),
      root_cause_families: [],
      primary_family: "unknown",
    };
  }

  for (const r of perRace) {
    for (const id of FAMILY_IDS) {
      scores[id] += r.scores?.[id] || 0;
      confidence[id] += r.confidence?.[id] || 0;
    }
    for (const id of r.root_cause_families || []) {
      if (freq[id] != null) freq[id] += 1;
    }
  }

  for (const id of FAMILY_IDS) {
    scores[id] = clamp01(scores[id] / n);
    confidence[id] = clamp01(confidence[id] / n);
  }

  const frequency_pct = {};
  for (const id of FAMILY_IDS) {
    frequency_pct[id] = Math.round((freq[id] / n) * 1000) / 10; // percent 1 decimal
  }

  const families = Object.entries(scores)
    .filter(([, s]) => s >= FAMILY_THRESHOLD)
    .sort((a, b) => b[1] - a[1])
    .map(([id]) => id);

  return {
    event_count: n,
    scores,
    confidence,
    frequency: freq,
    frequency_pct,
    root_cause_families: families.length ? families : ["unknown"],
    primary_family: (families[0] || "unknown"),
  };
}

/**
 * Improvement Priority from frequency × impact × score.
 * @param {{ scores: object, frequency_pct: object, event_count: number }} agg
 */
export function computeImprovementPriority(agg) {
  const items = [];
  for (const id of FAMILY_IDS) {
    if (id === "unknown" || id === "ops_data") continue;
    const score = agg.scores?.[id] || 0;
    const freqPct = (agg.frequency_pct?.[id] || 0) / 100;
    const impact = IMPACT_WEIGHT[id] ?? 0.3;
    if (score < 0.05 && freqPct < 0.05) continue;
    const priority_score = clamp01(score * 0.5 + freqPct * 0.35 + impact * 0.15 * Math.max(score, freqPct));
    items.push({
      family: id,
      proposal: id,
      score,
      frequency_pct: agg.frequency_pct?.[id] || 0,
      impact,
      priority_score,
    });
  }
  items.sort((a, b) => b.priority_score - a.priority_score);

  return items.map((it, i) => {
    let band = "C";
    if (i === 0 && it.priority_score >= 0.2) band = "A";
    else if (i <= 1 && it.priority_score >= 0.12) band = "B";
    else if (it.priority_score >= 0.25) band = "A";
    else if (it.priority_score >= 0.15) band = "B";
    return {
      ...it,
      priority: i + 1,
      priority_band: band,
    };
  });
}

export function bandLabel(band) {
  return band === "A" ? "Priority A" : band === "B" ? "Priority B" : "Priority C";
}
