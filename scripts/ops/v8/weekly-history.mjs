/**
 * Version8.1 — append-only weekly research history.
 * Path: development/history/weekly_history.json
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { repoRoot, weekIdJst } from "./calendar.mjs";

const HISTORY_REL = ["development", "history", "weekly_history.json"];

export function historyPath(devRoot) {
  return join(devRoot, "history", "weekly_history.json");
}

export function loadWeeklyHistory(devRoot) {
  const path = historyPath(devRoot);
  if (!existsSync(path)) return [];
  try {
    const raw = JSON.parse(readFileSync(path, "utf8"));
    if (Array.isArray(raw)) return raw;
    if (Array.isArray(raw.weeks)) return raw.weeks;
  } catch {
    /* empty */
  }
  return [];
}

/**
 * Upsert one week entry.
 * @param {object} entry
 * @param {{ devRoot?: string }} [opts]
 */
export function upsertWeeklyHistory(entry, opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const dir = join(devRoot, "history");
  mkdirSync(dir, { recursive: true });

  const weeks = loadWeeklyHistory(devRoot);
  const week = entry.week || entry.week_id || weekIdJst();
  const next = {
    week,
    decision: entry.decision || "no_improvement",
    hit_delta: entry.hit_delta ?? null,
    rank710_delta: entry.rank710_delta ?? null,
    primary_family: entry.primary_family ?? entry.root_cause ?? null,
    // Version8.2 Weekly Knowledge
    root_cause: entry.root_cause ?? entry.primary_family ?? null,
    validation_score: entry.validation_score ?? null,
    impact: entry.impact ?? null,
    proposals: Array.isArray(entry.proposals) ? entry.proposals : [],
    validation_pass_count: entry.validation_pass_count ?? null,
    validation_fail_count: entry.validation_fail_count ?? null,
    proposal_ids: entry.proposal_ids || [],
    recorded_at: new Date().toISOString(),
  };

  const idx = weeks.findIndex((w) => w.week === week);
  if (idx >= 0) weeks[idx] = { ...weeks[idx], ...next };
  else weeks.push(next);

  weeks.sort((a, b) => String(a.week).localeCompare(String(b.week)));
  writeFileSync(historyPath(devRoot), JSON.stringify(weeks, null, 2) + "\n", "utf8");
  return weeks;
}

/**
 * Derive rates from history for Research Metrics.
 * @param {object[]} weeks
 */
export function summarizeHistory(weeks) {
  const n = weeks.length;
  if (!n) {
    return {
      weeks: 0,
      accept_rate: 0,
      reject_rate: 0,
      no_improvement_rate: 0,
      improvement_success_rate: 0,
      avg_hit_delta: null,
      validation_pass_rate: 0,
      validation_reject_rate: 0,
      proposal_recurrence_rate: 0,
      root_cause_success: {},
    };
  }
  let accept = 0;
  let reject = 0;
  let noImp = 0;
  let hitSum = 0;
  let hitN = 0;
  let valPass = 0;
  let valFail = 0;
  let valTotal = 0;
  /** @type {Record<string, {accept: number, total: number}>} */
  const byCause = {};
  /** @type {Record<string, number>} */
  const familyWeeks = {};

  for (const w of weeks) {
    const d = String(w.decision || "");
    if (d === "accept") accept += 1;
    else if (d === "reject") reject += 1;
    else noImp += 1;
    if (typeof w.hit_delta === "number") {
      hitSum += w.hit_delta;
      hitN += 1;
    }
    const vp = Number(w.validation_pass_count) || 0;
    const vf = Number(w.validation_fail_count) || 0;
    if (vp + vf > 0) {
      valPass += vp;
      valFail += vf;
      valTotal += vp + vf;
    }
    const cause = w.root_cause || w.primary_family;
    if (cause) {
      familyWeeks[cause] = (familyWeeks[cause] || 0) + 1;
      if (!byCause[cause]) byCause[cause] = { accept: 0, total: 0 };
      byCause[cause].total += 1;
      if (d === "accept") byCause[cause].accept += 1;
    }
  }

  // Recurrence: families appearing in >1 week / distinct families
  const recurring = Object.values(familyWeeks).filter((c) => c > 1).length;
  const distinctFamilies = Object.keys(familyWeeks).length;

  const root_cause_success = {};
  for (const [k, v] of Object.entries(byCause)) {
    root_cause_success[k] =
      v.total > 0 ? Math.round((v.accept / v.total) * 1000) / 10 : 0;
  }

  return {
    weeks: n,
    accept_rate: Math.round((accept / n) * 1000) / 10,
    reject_rate: Math.round((reject / n) * 1000) / 10,
    no_improvement_rate: Math.round((noImp / n) * 1000) / 10,
    improvement_success_rate: Math.round((accept / n) * 1000) / 10,
    avg_hit_delta: hitN ? Math.round((hitSum / hitN) * 100) / 100 : null,
    validation_pass_rate:
      valTotal > 0 ? Math.round((valPass / valTotal) * 1000) / 10 : 0,
    validation_reject_rate:
      valTotal > 0 ? Math.round((valFail / valTotal) * 1000) / 10 : 0,
    proposal_recurrence_rate:
      distinctFamilies > 0
        ? Math.round((recurring / distinctFamilies) * 1000) / 10
        : 0,
    root_cause_success,
  };
}

function main() {
  const REPO = repoRoot();
  const path = join(REPO, ...HISTORY_REL);
  if (!existsSync(path)) {
    mkdirSync(join(REPO, "development", "history"), { recursive: true });
    writeFileSync(path, "[]\n", "utf8");
  }
  console.log(JSON.stringify({ path, weeks: loadWeeklyHistory(join(REPO, "development")) }, null, 2));
}

if (process.argv[1]?.endsWith("weekly-history.mjs")) {
  main();
}
