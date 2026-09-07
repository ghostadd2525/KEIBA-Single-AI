/**
 * Version8.4 — Research Knowledge Base (long-term Research assets).
 *
 * Analyzer / Validation read this KB instead of re-scanning weekly history.
 * Production Evidence / PE / CE / AI Core are never mutated.
 *
 * development/knowledge/
 *   root_causes.json | proposals.json | canary_results.json
 *   accepted_patterns.json | rejected_patterns.json
 * development/history/research_timeline.json
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
} from "node:fs";
import { dirname, join } from "node:path";
import { repoRoot, weekIdJst, assertResearchDay } from "./calendar.mjs";

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

export function knowledgeDir(devRoot) {
  return join(devRoot, "knowledge");
}

export function kbPaths(devRoot) {
  const k = knowledgeDir(devRoot);
  return {
    root: k,
    root_causes: join(k, "root_causes.json"),
    proposals: join(k, "proposals.json"),
    canary_results: join(k, "canary_results.json"),
    accepted_patterns: join(k, "accepted_patterns.json"),
    rejected_patterns: join(k, "rejected_patterns.json"),
    timeline: join(devRoot, "history", "research_timeline.json"),
  };
}

/** Human-readable proposal labels by family. */
export const PROPOSAL_LABELS = Object.freeze({
  candidate_pool: "Entry Threshold Safe",
  repick: "Repick Narrowing",
  delete: "Delete Expansion",
  purchase: "Purchase Coverage",
  confidence: "Confidence Recalibration",
  world: "World Selection",
  subworld: "Subworld Slice",
  ranking: "Ranking Calibration",
  features: "Feature Supply",
  ops_data: "Ops Data Fix",
  unknown: "Unknown",
});

export function proposalLabel(family) {
  return PROPOSAL_LABELS[family] || family;
}

/**
 * Knowledge Score:
 *   no data → 0.5
 *   else → 0.1 + 0.9 × (accepted / (accepted + rejected))
 * Example: 4 accept / 1 reject → 0.82
 */
export function computeKnowledgeScore(accepted, rejected) {
  const a = Math.max(0, Number(accepted) || 0);
  const r = Math.max(0, Number(rejected) || 0);
  if (a + r === 0) return 0.5;
  return round3(0.1 + 0.9 * (a / (a + r)));
}

export function ensureKnowledgeBase(devRoot) {
  const p = kbPaths(devRoot);
  mkdirSync(p.root, { recursive: true });
  mkdirSync(join(devRoot, "history"), { recursive: true });

  if (!existsSync(p.root_causes)) {
    writeJson(p.root_causes, {
      schema_version: "expect-v84-kb-root-causes/1.0",
      families: {},
      updated_at: null,
    });
  }
  if (!existsSync(p.proposals)) {
    writeJson(p.proposals, {
      schema_version: "expect-v84-kb-proposals/1.0",
      proposals: {},
      updated_at: null,
    });
  }
  if (!existsSync(p.canary_results)) {
    writeJson(p.canary_results, {
      schema_version: "expect-v84-kb-canary/1.0",
      results: [],
      updated_at: null,
    });
  }
  if (!existsSync(p.accepted_patterns)) {
    writeJson(p.accepted_patterns, {
      schema_version: "expect-v84-kb-accepted/1.0",
      patterns: [],
      next_id: 1,
      updated_at: null,
    });
  }
  if (!existsSync(p.rejected_patterns)) {
    writeJson(p.rejected_patterns, {
      schema_version: "expect-v84-kb-rejected/1.0",
      patterns: [],
      next_id: 1,
      updated_at: null,
    });
  }
  if (!existsSync(p.timeline)) {
    writeJson(p.timeline, []);
  }
  return p;
}

/**
 * Version8.8 — Approval Queue / Timeout → rejected_patterns.
 * Used by approval-queue.mjs (reject + approval_timeout).
 */
export function appendApprovalRejectedPattern(opts = {}) {
  const repo = opts.repo || repoRoot();
  const devRoot = join(repo, "development");
  const p = ensureKnowledgeBase(devRoot);
  const store = readJson(p.rejected_patterns, {
    schema_version: "expect-v85-kb-rejected/1.0",
    patterns: [],
    next_id: 1,
  });
  const n = Number(store.next_id) || (store.patterns?.length || 0) + 1;
  const patternId = `REJ-${String(n).padStart(3, "0")}`;
  store.patterns = Array.isArray(store.patterns) ? store.patterns : [];
  store.patterns.push({
    pattern_id: patternId,
    root_cause: opts.root_cause || "approval_workflow",
    proposal_family: opts.proposal_family || "approval_workflow",
    proposal: opts.proposal || opts.approval_id || "approval",
    rejected_week: opts.week_id || null,
    created_week: opts.week_id || null,
    last_used: opts.week_id || null,
    usage_count: 0,
    status: "active",
    reason: String(opts.reason || "rejected"),
    approval_id: opts.approval_id || null,
    auto: !!opts.auto,
    source: opts.source || "v88_approval_queue",
    hit_delta: opts.hit_delta ?? null,
  });
  store.next_id = n + 1;
  store.updated_at = new Date().toISOString();
  store.schema_version = "expect-v85-kb-rejected/1.0";
  writeJson(p.rejected_patterns, store);
  return patternId;
}

export function loadKnowledgeBase(devRoot) {
  const p = ensureKnowledgeBase(devRoot);
  return {
    paths: p,
    root_causes: readJson(p.root_causes, { families: {} }),
    proposals: readJson(p.proposals, { proposals: {} }),
    canary_results: readJson(p.canary_results, { results: [] }),
    accepted_patterns: readJson(p.accepted_patterns, { patterns: [], next_id: 1 }),
    rejected_patterns: readJson(p.rejected_patterns, { patterns: [], next_id: 1 }),
    timeline: readJson(p.timeline, []),
  };
}

/**
 * Similarity search against Knowledge Base (not weekly history).
 * Skips archived patterns for Accept hits. Uses decayed knowledge_score when present.
 * @param {string} family
 * @param {object} kb
 * @param {{ week_id?: string }} [opts]
 */
export function similaritySearch(family, kb, opts = {}) {
  const label = proposalLabel(family);
  const prop = kb.proposals?.proposals?.[family] || null;
  const acceptedAll = (kb.accepted_patterns?.patterns || []).filter(
    (x) => x.root_cause === family || x.proposal_family === family
  );
  const accepted = acceptedAll.filter((x) => (x.status || "active") !== "archived");
  const rejected = (kb.rejected_patterns?.patterns || []).filter(
    (x) =>
      ((x.status || "active") !== "archived") &&
      (x.root_cause === family ||
        x.proposal_family === family ||
        x.proposal === label ||
        (typeof x.proposal === "string" &&
          x.proposal.toLowerCase().includes(String(family).replace(/_/g, " "))))
  );

  const RELATED = {
    candidate_pool: ["ranking", "repick"],
    repick: ["ranking", "candidate_pool"],
    delete: ["candidate_pool"],
    ranking: ["repick", "candidate_pool", "confidence"],
    confidence: ["ranking"],
  };
  const related = RELATED[family] || [];
  const similarAccepted = (kb.accepted_patterns?.patterns || []).filter(
    (x) =>
      related.includes(x.root_cause) && (x.status || "active") !== "archived"
  );
  const similarRejected = (kb.rejected_patterns?.patterns || []).filter(
    (x) =>
      related.includes(x.root_cause) && (x.status || "active") !== "archived"
  );

  const same_proposal = Boolean(prop) || accepted.length > 0 || rejected.length > 0;
  const similar_proposals = [
    ...similarAccepted.map((x) => ({
      kind: "accepted",
      pattern_id: x.pattern_id,
      root_cause: x.root_cause,
      proposal: x.proposal,
      week: x.accepted_week,
      status: x.status || "active",
      similarity: 0.7,
    })),
    ...similarRejected.map((x) => ({
      kind: "rejected",
      pattern_id: x.pattern_id,
      root_cause: x.root_cause,
      proposal: x.proposal,
      week: x.rejected_week,
      reason: x.reason,
      similarity: 0.7,
    })),
  ];

  const past_rejected = rejected.map((x) => ({
    week: x.rejected_week,
    decision: "reject",
    root_cause: x.root_cause || family,
    label: x.proposal || label,
    reason: x.reason || null,
    similarity: 0.95,
    message: `Similar to ${x.rejected_week || "past"} Reject ${x.proposal || label}`,
  }));

  const past_accepted = accepted.map((x) => ({
    week: x.accepted_week,
    decision: "accept",
    root_cause: x.root_cause || family,
    label: x.proposal || label,
    pattern_id: x.pattern_id,
    status: x.status || "active",
    similarity: 0.95,
    message: `Similar to ${x.accepted_week || "past"} Accept ${x.pattern_id || label}`,
  }));

  const knowledge_score =
    typeof prop?.knowledge_score === "number"
      ? prop.knowledge_score
      : computeKnowledgeScore(
          prop?.accepted_count ?? accepted.length,
          prop?.rejected_count ?? rejected.length
        );

  return {
    schema_version: "expect-v85-similarity-search/1.0",
    query: { family, proposal: label, week_id: opts.week_id || null },
    same_proposal,
    similar_proposal: similar_proposals.length > 0,
    past_rejected: past_rejected.length > 0,
    past_accepted: past_accepted.length > 0,
    same_hits: prop
      ? [{ family, accepted: prop.accepted_count, rejected: prop.rejected_count }]
      : [],
    similar_proposals,
    rejected_hits: past_rejected,
    accepted_hits: past_accepted,
    knowledge_score,
    warnings: past_rejected.slice(0, 3),
  };
}

/**
 * Next pattern id PAT-001 …
 */
export function nextPatternId(store, prefix) {
  const n = Number(store.next_id) || (store.patterns?.length || 0) + 1;
  return `${prefix}-${String(n).padStart(3, "0")}`;
}

/**
 * Ingest Friday decision + canary into Knowledge Base + Timeline.
 * @param {{ week_id?: string, devRoot?: string, weekRoot?: string }} [opts]
 */
export function syncKnowledgeFromWeek(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weekId = opts.week_id || weekIdJst();
  const weekRoot = opts.weekRoot || join(devRoot, "weekly", weekId);
  const kb = loadKnowledgeBase(devRoot);
  const p = kb.paths;

  const decision = readJson(join(weekRoot, "fri-decision", "decision.json"), {});
  const validation = readJson(
    join(weekRoot, "tue-proposal", "proposal-validation.json"),
    readJson(join(devRoot, "analysis", "proposal-validation.json"), {})
  );
  const canary = readJson(
    join(weekRoot, "wed-canary", "ranked-run.json"),
    readJson(join(devRoot, "runs", "latest-canary-ranked.json"), {})
  );
  const baseline = readJson(join(weekRoot, "thu-baseline", "report.json"), {});
  const miss = readJson(join(devRoot, "analysis", "miss", "latest.json"), {});

  const decisionType = decision.decision || "no_improvement";
  const hitDelta =
    typeof decision.hit_delta === "number"
      ? decision.hit_delta
      : typeof decision.baseline_delta === "number"
        ? Math.round(decision.baseline_delta * 100)
        : null;
  const rank710 =
    typeof decision.rank710_delta === "number" ? decision.rank710_delta : null;

  const reasonFromBaseline =
    baseline?.comparison?.verdict === "no_measured_delta"
      ? "No measured 285R delta"
      : baseline?.comparison?.verdict === "regression" ||
          (typeof baseline?.comparison?.measured_delta_hit_at_1 === "number" &&
            baseline.comparison.measured_delta_hit_at_1 < 0)
        ? "285R Regression"
        : decision.reason || "Rejected by Friday gate";

  /** @type {string[]} */
  const acceptedIds = [];
  /** @type {string[]} */
  const rejectedIds = [];

  // Update root_causes summary from miss analysis
  const families = kb.root_causes.families || {};
  for (const [id, score] of Object.entries(miss.root_cause_scores || {})) {
    if (!families[id]) {
      families[id] = { observations: 0, last_score: 0, last_week: null };
    }
    families[id].observations += 1;
    families[id].last_score = score;
    families[id].last_week = weekId;
  }
  kb.root_causes = {
    schema_version: "expect-v84-kb-root-causes/1.0",
    families,
    updated_at: new Date().toISOString(),
  };

  // Canary results append
  const canaryResults = Array.isArray(kb.canary_results.results)
    ? [...kb.canary_results.results]
    : [];
  for (const r of canary.results || []) {
    canaryResults.push({
      week: weekId,
      proposal: r.proposal,
      status: r.status,
      verdict: r.verdict ?? null,
      validation_score: r.validation_score ?? null,
      gate: r.gate ?? null,
      recorded_at: new Date().toISOString(),
    });
  }
  kb.canary_results = {
    schema_version: "expect-v84-kb-canary/1.0",
    results: canaryResults.slice(-500),
    updated_at: new Date().toISOString(),
  };

  const proposals = { ...(kb.proposals.proposals || {}) };
  const validations = validation.validations || [];
  const primaryFamily =
    decision.root_cause ||
    miss.root_cause_family ||
    validations.find((v) => v.gate === "pass")?.family ||
    validations[0]?.family ||
    null;

  function bumpProposal(family, kind) {
    if (!family) return;
    if (!proposals[family]) {
      proposals[family] = {
        family,
        proposal: proposalLabel(family),
        accepted_count: 0,
        rejected_count: 0,
        knowledge_score: 0.5,
        last_week: null,
      };
    }
    if (kind === "accept") proposals[family].accepted_count += 1;
    if (kind === "reject") proposals[family].rejected_count += 1;
    proposals[family].knowledge_score = computeKnowledgeScore(
      proposals[family].accepted_count,
      proposals[family].rejected_count
    );
    proposals[family].last_week = weekId;
  }

  if (decisionType === "accept" && primaryFamily) {
    const id = nextPatternId(kb.accepted_patterns, "PAT");
    kb.accepted_patterns.patterns.push({
      pattern_id: id,
      root_cause: primaryFamily,
      proposal_family: primaryFamily,
      proposal: proposalLabel(primaryFamily),
      accepted_week: weekId,
      created_week: weekId,
      last_used: weekId,
      usage_count: 1,
      status: "active",
      last_revalidated: null,
      hit_delta: hitDelta,
      rank710_delta: rank710,
      validation_score:
        validations.find((v) => v.family === primaryFamily)?.validation_score ??
        null,
    });
    kb.accepted_patterns.next_id =
      (Number(kb.accepted_patterns.next_id) || 1) + 1;
    kb.accepted_patterns.updated_at = new Date().toISOString();
    kb.accepted_patterns.schema_version = "expect-v85-kb-accepted/1.0";
    acceptedIds.push(id);
    bumpProposal(primaryFamily, "accept");
  } else if (decisionType === "reject") {
    const fam = primaryFamily || "unknown";
    const id = nextPatternId(kb.rejected_patterns, "REJ");
    const entry = {
      pattern_id: id,
      root_cause: fam,
      proposal_family: fam,
      proposal: proposalLabel(fam),
      rejected_week: weekId,
      created_week: weekId,
      last_used: weekId,
      usage_count: 0,
      status: "active",
      reason: reasonFromBaseline,
      hit_delta: hitDelta,
    };
    kb.rejected_patterns.patterns.push(entry);
    kb.rejected_patterns.next_id =
      (Number(kb.rejected_patterns.next_id) || 1) + 1;
    kb.rejected_patterns.updated_at = new Date().toISOString();
    kb.rejected_patterns.schema_version = "expect-v85-kb-rejected/1.0";
    rejectedIds.push(id);
    bumpProposal(fam, "reject");
  } else {
    // no_improvement — still record validation fails as soft rejects? skip accept/reject counts
  }

  // Also record gate_blocked families lightly in proposals map for knowledge
  for (const v of validations) {
    const f = v.family || v.proposal;
    if (!f) continue;
    if (!proposals[f]) {
      proposals[f] = {
        family: f,
        proposal: proposalLabel(f),
        accepted_count: 0,
        rejected_count: 0,
        knowledge_score: 0.5,
        last_week: weekId,
      };
    }
    proposals[f].knowledge_score = computeKnowledgeScore(
      proposals[f].accepted_count,
      proposals[f].rejected_count
    );
  }

  kb.proposals = {
    schema_version: "expect-v84-kb-proposals/1.0",
    proposals,
    updated_at: new Date().toISOString(),
  };

  // Timeline upsert
  const timeline = Array.isArray(kb.timeline) ? [...kb.timeline] : [];
  const tIdx = timeline.findIndex((t) => t.week === weekId);
  const tEntry = {
    week: weekId,
    accepted: acceptedIds,
    rejected: rejectedIds,
    decision: decisionType,
    recorded_at: new Date().toISOString(),
  };
  if (tIdx >= 0) timeline[tIdx] = { ...timeline[tIdx], ...tEntry };
  else timeline.push(tEntry);
  timeline.sort((a, b) => String(a.week).localeCompare(String(b.week)));

  // Persist
  writeJson(p.root_causes, kb.root_causes);
  writeJson(p.proposals, kb.proposals);
  writeJson(p.canary_results, kb.canary_results);
  writeJson(p.accepted_patterns, kb.accepted_patterns);
  writeJson(p.rejected_patterns, kb.rejected_patterns);
  writeJson(p.timeline, timeline);

  // Week snapshot
  if (existsSync(weekRoot)) {
    const out = join(weekRoot, "reports");
    mkdirSync(out, { recursive: true });
    writeJson(join(out, "knowledge-sync.json"), {
      week: weekId,
      accepted: acceptedIds,
      rejected: rejectedIds,
      decision: decisionType,
    });
  }

  return {
    schema_version: "expect-v84-knowledge-sync/1.0",
    week_id: weekId,
    accepted: acceptedIds,
    rejected: rejectedIds,
    decision: decisionType,
    proposal_scores: Object.fromEntries(
      Object.entries(proposals).map(([k, v]) => [k, v.knowledge_score])
    ),
    pe_ce_untouched: true,
  };
}

/**
 * Summarize KB for Research Metrics.
 */
export function summarizeKnowledgeMetrics(devRoot) {
  const kb = loadKnowledgeBase(devRoot);
  const accepted = kb.accepted_patterns.patterns || [];
  const rejected = kb.rejected_patterns.patterns || [];
  const timeline = Array.isArray(kb.timeline) ? kb.timeline : [];
  const canary = kb.canary_results.results || [];

  // Pattern reuse: accepted patterns whose family appears again in later timeline
  let reuse = 0;
  const acceptedByWeek = {};
  for (const a of accepted) {
    if (!acceptedByWeek[a.accepted_week]) acceptedByWeek[a.accepted_week] = [];
    acceptedByWeek[a.accepted_week].push(a.root_cause);
  }
  const weeks = Object.keys(acceptedByWeek).sort();
  for (let i = 1; i < weeks.length; i++) {
    const prev = new Set(acceptedByWeek[weeks[i - 1]]);
    for (const f of acceptedByWeek[weeks[i]]) {
      if (prev.has(f)) reuse += 1;
    }
  }
  const reuseDenom = Math.max(1, accepted.length);
  const pattern_reuse_rate = round3(reuse / reuseDenom);

  // Knowledge hit: canary/validation queries that found same or similar (approx from canary with validation_score)
  // Use: fraction of proposal families that have any KB entry
  const propKeys = Object.keys(kb.proposals.proposals || {});
  const withHistory = propKeys.filter((k) => {
    const p = kb.proposals.proposals[k];
    return (p.accepted_count || 0) + (p.rejected_count || 0) > 0;
  });
  const knowledge_hit_rate =
    propKeys.length > 0 ? round3(withHistory.length / propKeys.length) : 0;

  // Similar proposal rate: rejected+accepted that have related family siblings
  let similar = 0;
  for (const a of accepted) {
    if (
      rejected.some((r) => r.root_cause === a.root_cause) ||
      accepted.filter((x) => x.root_cause === a.root_cause).length > 1
    ) {
      similar += 1;
    }
  }
  const similar_proposal_rate =
    accepted.length + rejected.length > 0
      ? round3(similar / Math.max(1, accepted.length))
      : 0;

  return {
    pattern_reuse_rate_pct: Math.round(pattern_reuse_rate * 1000) / 10,
    accepted_pattern_count: accepted.length,
    rejected_pattern_count: rejected.length,
    knowledge_hit_rate_pct: Math.round(knowledge_hit_rate * 1000) / 10,
    similar_proposal_rate_pct: Math.round(similar_proposal_rate * 1000) / 10,
    timeline_weeks: timeline.length,
    canary_result_count: canary.length,
    knowledge_scores: Object.fromEntries(
      Object.entries(kb.proposals.proposals || {}).map(([k, v]) => [
        k,
        v.knowledge_score,
      ])
    ),
  };
}

function main() {
  if (!process.argv.includes("--allow-weekend")) {
    assertResearchDay({ purpose: "v8.4:knowledge-sync" });
  }
  const wi = process.argv.indexOf("--week-id");
  const week_id = wi >= 0 ? process.argv[wi + 1] : undefined;
  const cmd = process.argv.includes("--search")
    ? "search"
    : process.argv.includes("--ensure")
      ? "ensure"
      : "sync";

  const REPO = repoRoot();
  const devRoot = join(REPO, "development");

  if (cmd === "ensure") {
    ensureKnowledgeBase(devRoot);
    console.log(JSON.stringify({ ok: true, paths: kbPaths(devRoot) }, null, 2));
    return;
  }
  if (cmd === "search") {
    const fi = process.argv.indexOf("--family");
    const family = fi >= 0 ? process.argv[fi + 1] : "candidate_pool";
    const kb = loadKnowledgeBase(devRoot);
    console.log(JSON.stringify(similaritySearch(family, kb, { week_id }), null, 2));
    return;
  }
  console.log(JSON.stringify(syncKnowledgeFromWeek({ week_id }), null, 2));
}

if (process.argv[1]?.endsWith("knowledge-base.mjs")) {
  try {
    main();
  } catch (e) {
    console.error(e && e.message ? e.message : e);
    process.exit(e && e.code === "V8_RESEARCH_WEEKEND_BLOCKED" ? 3 : 1);
  }
}
