/**
 * Version8.1 — Proposal ranking from Analyzer improvement_priority.
 * Canary should evaluate in this order.
 */
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  writeFileSync,
} from "node:fs";
import { join } from "node:path";
import { computeImprovementPriority, bandLabel } from "./root-cause-score.mjs";
import { loadKnowledgeBase, similaritySearch } from "./knowledge-base.mjs";
import { repoRoot, weekIdJst } from "./calendar.mjs";

function readJson(path) {
  if (!existsSync(path)) return null;
  try {
    return JSON.parse(readFileSync(path, "utf8"));
  } catch {
    return null;
  }
}

/**
 * Rank proposal families; optionally attach existing IMP-* ids.
 * @param {{ week_id?: string, devRoot?: string }} [opts]
 */
export function rankProposals(opts = {}) {
  const REPO = repoRoot();
  const devRoot = opts.devRoot || join(REPO, "development");
  const weekId = opts.week_id || weekIdJst();
  const miss = readJson(join(devRoot, "analysis", "miss", "latest.json"));
  const kb = loadKnowledgeBase(devRoot);
  const priority =
    Array.isArray(miss?.improvement_priority) && miss.improvement_priority.length
      ? miss.improvement_priority
      : computeImprovementPriority({
          scores: miss?.root_cause_scores || {},
          frequency_pct: miss?.root_cause_frequency_pct || {},
          event_count: miss?.event_count || 0,
        });

  const proposalsDir = join(devRoot, "proposals");
  const proposalFiles = existsSync(proposalsDir)
    ? readdirSync(proposalsDir).filter((f) => f.endsWith(".json") && !f.startsWith("_"))
    : [];

  const proposalsByFamily = {};
  for (const f of proposalFiles) {
    const p = readJson(join(proposalsDir, f));
    if (!p) continue;
    const family =
      p.metadata?.target_root_cause_family ||
      p.metadata?.analyzer_root_cause_family ||
      (p.event_types?.[0] === "miss" ? miss?.root_cause_family : null);
    if (!family) continue;
    if (!proposalsByFamily[family]) proposalsByFamily[family] = [];
    proposalsByFamily[family].push(p.proposal_id);
  }

  const ranking = priority.map((row) => {
    const family = row.family;
    const sim = similaritySearch(family, kb, { week_id: weekId });
    return {
      proposal: row.proposal || row.family,
      family: row.family,
      priority: row.priority,
      priority_band: row.priority_band,
      priority_label: bandLabel(row.priority_band),
      score: row.score,
      frequency_pct: row.frequency_pct,
      impact: row.impact,
      priority_score: row.priority_score,
      proposal_ids: proposalsByFamily[row.family] || [],
      knowledge_score: sim.knowledge_score,
      similarity: {
        same_proposal: sim.same_proposal,
        similar_proposal: sim.similar_proposal,
        past_rejected: sim.past_rejected,
        past_accepted: sim.past_accepted,
      },
    };
  });

  const doc = {
    schema_version: "expect-v84-proposal-ranking/1.0",
    week_id: weekId,
    generated_at: new Date().toISOString(),
    ranking,
    canary_order: ranking.map((r) => ({
      priority: r.priority,
      proposal: r.proposal,
      proposal_ids: r.proposal_ids,
      knowledge_score: r.knowledge_score,
    })),
    note: "Canary evaluates Priority order after Validation Gate. KB similarity pre-checked. PE/CE unchanged.",
  };

  mkdirSync(join(devRoot, "analysis"), { recursive: true });
  writeFileSync(
    join(devRoot, "analysis", "proposal-ranking.json"),
    JSON.stringify(doc, null, 2) + "\n",
    "utf8"
  );

  const weekRoot = join(devRoot, "weekly", weekId);
  if (existsSync(weekRoot)) {
    const tue = join(weekRoot, "tue-proposal");
    mkdirSync(tue, { recursive: true });
    writeFileSync(
      join(tue, "proposal-ranking.json"),
      JSON.stringify(doc, null, 2) + "\n",
      "utf8"
    );
  }

  return doc;
}

function main() {
  const wi = process.argv.indexOf("--week-id");
  const week_id = wi >= 0 ? process.argv[wi + 1] : undefined;
  console.log(JSON.stringify(rankProposals({ week_id }), null, 2));
}

if (process.argv[1]?.endsWith("rank-proposals.mjs")) {
  main();
}
