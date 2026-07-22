/**
 * ホームヒートマップ — 過去◎的中率（セグメント集計）
 * schema: expect-stats-heatmap/1.0
 */

export const HEATMAP_SCHEMA = "expect-stats-heatmap/1.0";

export const DISTANCE_COLS = [
  { surf: "芝", bucket: 1200, label: "芝1200" },
  { surf: "芝", bucket: 1600, label: "芝1600" },
  { surf: "芝", bucket: 2000, label: "芝2000" },
  { surf: "芝", bucket: 2400, label: "芝2400" },
  { surf: "ダ", bucket: 1200, label: "ダ1200" },
  { surf: "ダ", bucket: 1600, label: "ダ1600" },
  { surf: "ダ", bucket: 2000, label: "ダ2000" },
  { surf: "ダ", bucket: 2400, label: "ダ2400" },
];

export const GOING_COLS = [
  { key: "良", label: "良" },
  { key: "稍重", label: "稍重" },
  { key: "重", label: "重" },
  { key: "不良", label: "不良" },
];

export const BAND_LABEL = { high: "高い", medium: "ふつう", low: "低い", unknown: "—" };

export function hitRateBand(rate) {
  if (rate == null || !Number.isFinite(Number(rate))) return "unknown";
  const r = Number(rate) > 1 ? Number(rate) / 100 : Number(rate);
  if (r >= 0.6) return "high";
  if (r >= 0.35) return "medium";
  return "low";
}

export function hitRatePercent(rate) {
  if (rate == null || !Number.isFinite(Number(rate))) return null;
  const r = Number(rate) > 1 ? Number(rate) : Number(rate) * 100;
  return Math.round(r);
}

export function normalizeGoing(raw) {
  const s = String(raw || "").trim();
  if (!s) return "";
  if (s === "稍" || s === "稍重") return "稍重";
  if (s === "良" || s === "重" || s === "不良") return s;
  return s;
}

export function venuesFromSegmentKeys(segments, segmentsGoing) {
  const set = new Set();
  for (const key of Object.keys(segments || {})) {
    const v = String(key).split("|")[0];
    if (v) set.add(v);
  }
  for (const key of Object.keys(segmentsGoing || {})) {
    const v = String(key).split("|")[0];
    if (v) set.add(v);
  }
  return Array.from(set).sort();
}

function cellFromSegment(seg, overall) {
  if (!seg || seg.n == null || Number(seg.n) < 1) {
    return { hit_rate: null, n: 0, band: "unknown", label: "—" };
  }
  const rate = seg.hit_rate != null ? Number(seg.hit_rate) : overall;
  const band = hitRateBand(rate);
  return {
    hit_rate: rate,
    n: Number(seg.n),
    band,
    label: BAND_LABEL[band] || "—",
    pct: hitRatePercent(rate),
  };
}

export function buildHeatmapPayload(table, venueFilter) {
  const segments = table?.segments || {};
  const segmentsGoing = table?.segments_going || {};
  const overall = Number(table?.overall_hit_rate) || 218 / 285;
  let venues = venuesFromSegmentKeys(segments, segmentsGoing);
  if (venueFilter && venueFilter.length) {
    const allow = new Set(venueFilter);
    venues = venues.filter((v) => allow.has(v));
  }

  const distance = {
    venues,
    cols: DISTANCE_COLS.map((c) => c.label),
    rows: venues.map((venue) => ({
      venue,
      cells: DISTANCE_COLS.map((c) => {
        const key = `${venue}|${c.surf}|${c.bucket}`;
        return cellFromSegment(segments[key], overall);
      }),
    })),
  };

  const condition = {
    cols: GOING_COLS.map((c) => c.label),
    rows: [],
  };
  for (const venue of venues) {
    for (const surf of ["芝", "ダ"]) {
      condition.rows.push({
        venue,
        surf,
        label: `${venue} ${surf}`,
        cells: GOING_COLS.map((goingCol) => {
          const key = `${venue}|${surf}|${goingCol.key}`;
          return cellFromSegment(segmentsGoing[key], overall);
        }),
      });
    }
  }

  return {
    schema_version: HEATMAP_SCHEMA,
    corpus: table?.corpus || "285R",
    overall_hit_rate: overall,
    min_samples: Number(table?.min_samples) || 3,
    updated_at: table?.generated_at || table?.updated_at || null,
    races_evaluated: Number(table?.races_evaluated) || 0,
    distance,
    condition,
    source: table?.source || "segment-hit-rates",
  };
}
