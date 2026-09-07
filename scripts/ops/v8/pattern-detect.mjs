/**
 * Version8.1 — cumulative pattern detection (past N weeks + current).
 */
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { FAMILY_IDS } from "./root-cause-score.mjs";
import { repoRoot, weekIdJst } from "./calendar.mjs";

function readJson(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

function listWeekIds(weeklyRoot) {
  if (!existsSync(weeklyRoot)) return [];
  return readdirSync(weeklyRoot, { withFileTypes: true })
    .filter((d) => d.isDirectory() && /^\d{4}-W\d{2}$/.test(d.name))
    .map((d) => d.name)
    .sort();
}

/**
 * @param {{ week_id?: string, weeks?: number, devRoot?: string }} [opts]
 */
export function detectPatterns(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weeks = Math.max(1, Number(opts.weeks) || 4);
  const currentWeek = opts.week_id || weekIdJst();
  const weeklyRoot = join(devRoot, "weekly");

  const weekIds = listWeekIds(weeklyRoot).filter((id) => id <= currentWeek);
  const window = weekIds.slice(-weeks);

  const familyHits = Object.fromEntries(FAMILY_IDS.map((id) => [id, 0]));
  let raceTotal = 0;
  const week_summaries = [];

  // Current analysis (may be newer than weekly copy)
  const currentMiss = readJson(join(devRoot, "analysis", "miss", "latest.json"));
  if (currentMiss && Array.isArray(currentMiss.per_race)) {
    for (const r of currentMiss.per_race) {
      raceTotal += 1;
      for (const id of r.root_cause_families || []) {
        if (familyHits[id] != null) familyHits[id] += 1;
      }
    }
  }

  for (const wid of window) {
    const miss =
      readJson(join(weeklyRoot, wid, "mon-analyzer", "miss-latest.json")) ||
      readJson(join(weeklyRoot, wid, "mon-analyzer", "pattern.json"));
    const scores = miss?.root_cause_scores || null;
    const freq = miss?.root_cause_frequency_pct || null;
    week_summaries.push({
      week: wid,
      primary_family: miss?.root_cause_family || null,
      scores,
      frequency_pct: freq,
      event_count: miss?.event_count ?? null,
    });
    // Prefer weekly per_race if current already counted — skip double count for current week file
    if (wid === currentWeek && currentMiss?.per_race?.length) continue;
    if (Array.isArray(miss?.per_race)) {
      for (const r of miss.per_race) {
        raceTotal += 1;
        for (const id of r.root_cause_families || []) {
          if (familyHits[id] != null) familyHits[id] += 1;
        }
      }
    }
  }

  const distribution_pct = {};
  for (const id of FAMILY_IDS) {
    distribution_pct[id] =
      raceTotal > 0 ? Math.round((familyHits[id] / raceTotal) * 1000) / 10 : 0;
  }

  const ranked = Object.entries(distribution_pct)
    .filter(([, p]) => p > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([family, pct]) => ({ family, pct }));

  return {
    schema_version: "expect-v81-pattern/1.0",
    week_id: currentWeek,
    window_weeks: weeks,
    weeks_included: window,
    race_total: raceTotal,
    distribution_pct,
    ranked,
    week_summaries,
    generated_at: new Date().toISOString(),
  };
}

export function writePatternReport(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weekId = opts.week_id || weekIdJst();
  const doc = detectPatterns({ ...opts, week_id: weekId, devRoot });
  const outDir = join(devRoot, "analysis", "patterns");
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "latest.json"), JSON.stringify(doc, null, 2) + "\n", "utf8");
  writeFileSync(join(outDir, `${weekId}.json`), JSON.stringify(doc, null, 2) + "\n", "utf8");

  const weekMon = join(devRoot, "weekly", weekId, "mon-analyzer");
  if (existsSync(join(devRoot, "weekly", weekId))) {
    mkdirSync(weekMon, { recursive: true });
    writeFileSync(join(weekMon, "pattern.json"), JSON.stringify(doc, null, 2) + "\n", "utf8");
  }
  return doc;
}

function main() {
  const i = process.argv.indexOf("--weeks");
  const weeks = i >= 0 ? Number(process.argv[i + 1]) : 4;
  const wi = process.argv.indexOf("--week-id");
  const week_id = wi >= 0 ? process.argv[wi + 1] : undefined;
  const doc = writePatternReport({ weeks, week_id });
  console.log(JSON.stringify(doc, null, 2));
}

const isCli =
  process.argv[1] &&
  String(process.argv[1]).replace(/\\/g, "/").endsWith("pattern-detect.mjs");
if (isCli) main();
