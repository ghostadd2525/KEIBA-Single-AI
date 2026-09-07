/**
 * Version8.5 — Research Governance (KB self-management).
 *
 * Aging / Revalidation / Knowledge Decay / Duplicate Merge / Dashboard
 * Research only — never drives Production decisions. PE/CE/AI untouched.
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { dirname, join } from "node:path";
import {
  loadKnowledgeBase,
  kbPaths,
  ensureKnowledgeBase,
  computeKnowledgeScore,
} from "./knowledge-base.mjs";
import { repoRoot, weekIdJst, assertResearchDay } from "./calendar.mjs";

/** Weeks unused before active → stale */
export const STALE_AFTER_WEEKS = 8;
/** Weeks unused (or stale age) before → archived */
export const ARCHIVE_AFTER_WEEKS = 16;
/** Revalidate accepted patterns at least every N weeks */
export const REVALIDATE_EVERY_WEEKS = 6;
/** Linear decay per unused week (0.92 → ~0.74 over ~26 weeks) */
export const DECAY_PER_WEEK = 0.008;
/** Floor for decayed knowledge score */
export const DECAY_FLOOR = 0.35;

function readJson(path, fallback) {
  if (!existsSync(path)) return fallback;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return fallback;
  }
}

function writeJson(path, doc) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(doc, null, 2) + "\n", "utf8");
}

function round3(x) {
  return Math.round(x * 1000) / 1000;
}

export function parseWeekId(weekId) {
  const m = String(weekId || "").match(/^(\d{4})-W(\d{2})$/);
  if (!m) return null;
  return { year: Number(m[1]), week: Number(m[2]) };
}

/** Approximate ISO-week distance. */
export function weekDistance(a, b) {
  const pa = parseWeekId(a);
  const pb = parseWeekId(b);
  if (!pa || !pb) return 0;
  return Math.abs((pa.year - pb.year) * 52 + (pa.week - pb.week));
}

/**
 * Knowledge Decay: unused time reduces score.
 * Example: 0.92 unused 26w → ~0.74
 */
export function applyKnowledgeDecay(baseScore, weeksUnused) {
  const base = Number(baseScore);
  if (!Number.isFinite(base)) return DECAY_FLOOR;
  const w = Math.max(0, Number(weeksUnused) || 0);
  const decayed = base * (1 - DECAY_PER_WEEK * w);
  return round3(Math.max(DECAY_FLOOR, Math.min(1, decayed)));
}

/**
 * Ensure lifecycle fields on a pattern.
 */
export function normalizePatternLifecycle(pat, weekId) {
  const created =
    pat.created_week || pat.accepted_week || pat.rejected_week || weekId;
  return {
    ...pat,
    created_week: created,
    last_used: pat.last_used || created,
    usage_count: Number(pat.usage_count) || 0,
    status: pat.status || "active",
    last_revalidated: pat.last_revalidated || null,
    revalidation_result: pat.revalidation_result || null,
  };
}

/**
 * Aging transition: active → stale → archived
 */
export function agePattern(pat, currentWeek) {
  const p = normalizePatternLifecycle(pat, currentWeek);
  if (p.status === "archived") return p;

  const unused = weekDistance(currentWeek, p.last_used || p.created_week);
  let status = p.status || "active";
  let reason = null;

  if (unused >= ARCHIVE_AFTER_WEEKS) {
    status = "archived";
    reason = `unused_${unused}w_archived`;
  } else if (unused >= STALE_AFTER_WEEKS || status === "stale") {
    if (status !== "archived") {
      status = "stale";
      reason = reason || `unused_${unused}w_stale`;
    }
  }

  return {
    ...p,
    status,
    weeks_unused: unused,
    aging_reason: reason,
  };
}

/**
 * Pattern Revalidation against latest 285R / baseline report.
 * No improvement / regression → stale.
 */
export function revalidatePattern(pat, baseline, currentWeek) {
  const p = normalizePatternLifecycle(pat, currentWeek);
  if (p.status === "archived") {
    return { ...p, revalidation_skipped: true };
  }

  const since =
    p.last_revalidated != null
      ? weekDistance(currentWeek, p.last_revalidated)
      : weekDistance(currentWeek, p.created_week || currentWeek);

  if (since < REVALIDATE_EVERY_WEEKS && p.last_revalidated) {
    return { ...p, revalidation_skipped: true };
  }

  const delta = baseline?.comparison?.measured_delta_hit_at_1;
  const verdict = baseline?.comparison?.verdict || null;
  let result = "hold";
  let nextStatus = p.status;

  if (
    verdict === "no_measured_delta" ||
    delta === null ||
    delta === undefined
  ) {
    result = "no_improvement";
    nextStatus = "stale";
  } else if (typeof delta === "number" && delta < 0) {
    result = "regression";
    nextStatus = "stale";
  } else if (typeof delta === "number" && delta > 0) {
    result = "still_improving";
    nextStatus = "active";
  } else {
    result = "no_improvement";
    nextStatus = "stale";
  }

  return {
    ...p,
    status: nextStatus,
    last_revalidated: currentWeek,
    revalidation_result: result,
    revalidation_skipped: false,
  };
}

/**
 * Duplicate Merge candidates: same root_cause (+ optional same proposal label).
 */
export function findMergeCandidates(patterns) {
  const active = (patterns || []).filter(
    (p) => (p.status || "active") !== "archived"
  );
  /** @type {Record<string, object[]>} */
  const byKey = {};
  for (const p of active) {
    const key = `${p.root_cause || "unknown"}::${p.proposal || p.proposal_family || ""}`;
    if (!byKey[key]) byKey[key] = [];
    byKey[key].push(p);
  }
  const candidates = [];
  for (const [key, group] of Object.entries(byKey)) {
    if (group.length < 2) continue;
    candidates.push({
      schema_version: "expect-v85-merge-candidate/1.0",
      key,
      root_cause: group[0].root_cause,
      proposal: group[0].proposal,
      pattern_ids: group.map((g) => g.pattern_id),
      status: "merge_candidate",
      note: "Similar patterns — consider merge (Research only)",
    });
  }
  // Also soft-merge same root_cause with different labels if 3+
  /** @type {Record<string, object[]>} */
  const byCause = {};
  for (const p of active) {
    const c = p.root_cause || "unknown";
    if (!byCause[c]) byCause[c] = [];
    byCause[c].push(p);
  }
  for (const [cause, group] of Object.entries(byCause)) {
    if (group.length < 3) continue;
    const ids = group.map((g) => g.pattern_id).sort();
    const already = candidates.some(
      (c) => c.root_cause === cause && c.pattern_ids.length === ids.length
    );
    if (already) continue;
    candidates.push({
      schema_version: "expect-v85-merge-candidate/1.0",
      key: `${cause}::*`,
      root_cause: cause,
      proposal: null,
      pattern_ids: ids,
      status: "merge_candidate",
      note: "Multiple patterns share root_cause — review for consolidation",
    });
  }
  return candidates;
}

/**
 * Touch pattern usage when Similarity Search hits it (Research).
 */
export function touchPatternUsage(pat, weekId) {
  const p = normalizePatternLifecycle(pat, weekId);
  if (p.status === "archived") return p;
  return {
    ...p,
    last_used: weekId,
    usage_count: (Number(p.usage_count) || 0) + 1,
    status: p.status === "stale" ? "active" : p.status, // reuse revives stale → active
  };
}

/**
 * Run full governance pass.
 * @param {{ week_id?: string, devRoot?: string, weekRoot?: string }} [opts]
 */
export function runGovernance(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weekId = opts.week_id || weekIdJst();
  const weekRoot =
    opts.weekRoot || join(devRoot, "weekly", weekId);

  ensureKnowledgeBase(devRoot);
  const kb = loadKnowledgeBase(devRoot);
  const p = kb.paths;
  const baseline = readJson(join(weekRoot, "thu-baseline", "report.json"), null);

  // Age + revalidate accepted
  const accepted = (kb.accepted_patterns.patterns || []).map((pat) => {
    let next = agePattern(pat, weekId);
    next = revalidatePattern(next, baseline, weekId);
    // Re-age after revalidation may have set stale
    if (next.status === "stale") {
      const unused = weekDistance(weekId, next.last_used || next.created_week);
      if (unused >= ARCHIVE_AFTER_WEEKS) next.status = "archived";
    }
    return next;
  });

  // Age rejected (no revalidation against 285R improvement)
  const rejected = (kb.rejected_patterns.patterns || []).map((pat) =>
    agePattern(pat, weekId)
  );

  // Decay proposal knowledge scores
  const proposals = { ...(kb.proposals.proposals || {}) };
  for (const [family, row] of Object.entries(proposals)) {
    const base = computeKnowledgeScore(
      row.accepted_count || 0,
      row.rejected_count || 0
    );
    const last = row.last_week || weekId;
    const unused = weekDistance(weekId, last);
    const decayed = applyKnowledgeDecay(base, unused);
    proposals[family] = {
      ...row,
      knowledge_score_raw: base,
      knowledge_score: decayed,
      weeks_unused: unused,
      last_week: row.last_week || null,
    };
  }

  const merge_candidates = findMergeCandidates(accepted);

  kb.accepted_patterns = {
    ...kb.accepted_patterns,
    schema_version: "expect-v85-kb-accepted/1.0",
    patterns: accepted,
    updated_at: new Date().toISOString(),
  };
  kb.rejected_patterns = {
    ...kb.rejected_patterns,
    schema_version: "expect-v85-kb-rejected/1.0",
    patterns: rejected,
    updated_at: new Date().toISOString(),
  };
  kb.proposals = {
    schema_version: "expect-v85-kb-proposals/1.0",
    proposals,
    updated_at: new Date().toISOString(),
  };

  writeJson(p.accepted_patterns, kb.accepted_patterns);
  writeJson(p.rejected_patterns, kb.rejected_patterns);
  writeJson(p.proposals, kb.proposals);

  const mergePath = join(knowledgeDirSafe(devRoot), "merge_candidates.json");
  writeJson(mergePath, {
    schema_version: "expect-v85-merge-candidates/1.0",
    week_id: weekId,
    candidates: merge_candidates,
    updated_at: new Date().toISOString(),
    research_only: true,
    production_untouched: true,
  });

  const dashboard = buildGovernanceDashboard({
    weekId,
    accepted,
    rejected,
    proposals,
    merge_candidates,
  });
  writeJson(join(knowledgeDirSafe(devRoot), "governance-dashboard.json"), dashboard);

  if (existsSync(weekRoot)) {
    const reports = join(weekRoot, "reports");
    mkdirSync(reports, { recursive: true });
    writeJson(join(reports, "governance.json"), dashboard);
  }

  return {
    schema_version: "expect-v85-governance-run/1.0",
    week_id: weekId,
    dashboard,
    merge_candidates,
    pe_ce_untouched: true,
    research_only: true,
  };
}

function knowledgeDirSafe(devRoot) {
  return join(devRoot, "knowledge");
}

export function buildGovernanceDashboard({
  weekId,
  accepted,
  rejected,
  proposals,
  merge_candidates,
}) {
  const all = [...(accepted || []), ...(rejected || [])];
  const active = all.filter((p) => (p.status || "active") === "active");
  const stale = all.filter((p) => p.status === "stale");
  const archived = all.filter((p) => p.status === "archived");
  const n = all.length || 1;

  const ages = all.map((p) =>
    weekDistance(weekId, p.created_week || p.accepted_week || weekId)
  );
  const avgLife =
    ages.length > 0
      ? round3(ages.reduce((a, b) => a + b, 0) / ages.length)
      : 0;

  const scores = Object.values(proposals || {}).map(
    (r) => Number(r.knowledge_score) || 0
  );
  const avgKs =
    scores.length > 0
      ? round3(scores.reduce((a, b) => a + b, 0) / scores.length)
      : 0.5;

  return {
    schema_version: "expect-v85-governance-dashboard/1.0",
    week_id: weekId,
    generated_at: new Date().toISOString(),
    active_pattern_count: active.length,
    stale_pattern_count: stale.length,
    archived_pattern_count: archived.length,
    merge_candidate_count: (merge_candidates || []).length,
    average_knowledge_score: avgKs,
    active_rate_pct: Math.round((active.length / n) * 1000) / 10,
    stale_rate_pct: Math.round((stale.length / n) * 1000) / 10,
    archive_rate_pct: Math.round((archived.length / n) * 1000) / 10,
    average_pattern_lifetime_weeks: avgLife,
    merge_candidates: merge_candidates || [],
    active_patterns: active.map((p) => p.pattern_id),
    stale_patterns: stale.map((p) => p.pattern_id),
    archived_patterns: archived.map((p) => p.pattern_id),
    safety: {
      research_only: true,
      production_decision_influence: false,
      pe_ce_untouched: true,
    },
  };
}

export function summarizeGovernanceMetrics(devRoot) {
  const dash = readJson(
    join(devRoot, "knowledge", "governance-dashboard.json"),
    null
  );
  if (!dash) {
    return {
      active_rate_pct: 0,
      stale_rate_pct: 0,
      archive_rate_pct: 0,
      merge_candidate_count: 0,
      average_pattern_lifetime_weeks: 0,
      average_knowledge_score: 0.5,
    };
  }
  return {
    active_rate_pct: dash.active_rate_pct,
    stale_rate_pct: dash.stale_rate_pct,
    archive_rate_pct: dash.archive_rate_pct,
    merge_candidate_count: dash.merge_candidate_count,
    average_pattern_lifetime_weeks: dash.average_pattern_lifetime_weeks,
    average_knowledge_score: dash.average_knowledge_score,
  };
}

function main() {
  if (!process.argv.includes("--allow-weekend")) {
    assertResearchDay({ purpose: "v8.5:governance" });
  }
  const wi = process.argv.indexOf("--week-id");
  const week_id = wi >= 0 ? process.argv[wi + 1] : undefined;
  console.log(JSON.stringify(runGovernance({ week_id }), null, 2));
}

if (process.argv[1]?.endsWith("governance.mjs")) {
  try {
    main();
  } catch (e) {
    console.error(e && e.message ? e.message : e);
    process.exit(e && e.code === "V8_RESEARCH_WEEKEND_BLOCKED" ? 3 : 1);
  }
}
