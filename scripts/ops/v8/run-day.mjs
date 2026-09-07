#!/usr/bin/env node
/**
 * Version8 weekday research runner.
 *
 * Wraps existing improve:* pipeline + weekly artifact folders.
 * Blocks Sat/Sun JST unless --allow-weekend (ops override only).
 *
 * Usage:
 *   node scripts/ops/v8/run-day.mjs --day mon
 *   node scripts/ops/v8/run-day.mjs --day fri
 *   node scripts/ops/v8/run-day.mjs --day week
 */
import { spawnSync } from "node:child_process";
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readFileSync,
  writeFileSync,
  cpSync,
} from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  assertResearchDay,
  jstParts,
  loadTaxonomy,
  repoRoot,
  weekIdJst,
} from "./calendar.mjs";
import { expireOverdueApprovals } from "./approval-queue.mjs";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO = repoRoot();
const WEEKLY = join(REPO, "development", "weekly");
const TEMPLATE = join(WEEKLY, "_TEMPLATE");

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i >= 0 && process.argv[i + 1]) return process.argv[i + 1];
  return fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function runNode(scriptRel, extraArgs = []) {
  const script = join(REPO, scriptRel);
  const r = spawnSync(process.execPath, [script, ...extraArgs], {
    cwd: REPO,
    encoding: "utf8",
    stdio: ["ignore", "pipe", "pipe"],
  });
  if (r.stdout) process.stdout.write(r.stdout);
  if (r.stderr) process.stderr.write(r.stderr);
  if (r.status !== 0) {
    const err = new Error(`Command failed (${r.status}): ${scriptRel}`);
    err.status = r.status;
    throw err;
  }
  return r;
}

function ensureWeekDir(weekId) {
  const root = join(WEEKLY, weekId);
  const stages = [
    "mon-analyzer",
    "tue-proposal",
    "wed-canary",
    "thu-baseline",
    "fri-decision",
    "sat-deploy",
    "reports",
  ];
  mkdirSync(root, { recursive: true });
  for (const s of stages) mkdirSync(join(root, s), { recursive: true });
  const manifestoPath = join(root, "manifesto.json");
  if (!existsSync(manifestoPath)) {
    const tpl = JSON.parse(
      readFileSync(join(TEMPLATE, "manifesto.json"), "utf8")
    );
    tpl.week_id = weekId;
    tpl.created_at = new Date().toISOString();
    writeFileSync(manifestoPath, JSON.stringify(tpl, null, 2) + "\n", "utf8");
  } else {
    // Merge V8.6 stage keys if missing
    try {
      const doc = JSON.parse(readFileSync(manifestoPath, "utf8"));
      const tpl = JSON.parse(
        readFileSync(join(TEMPLATE, "manifesto.json"), "utf8")
      );
      doc.stages = doc.stages || {};
      let changed = false;
      for (const [k, v] of Object.entries(tpl.stages || {})) {
        if (!doc.stages[k]) {
          doc.stages[k] = { ...v };
          changed = true;
        }
      }
      if (changed) {
        doc.schema_version = tpl.schema_version || doc.schema_version;
        writeFileSync(manifestoPath, JSON.stringify(doc, null, 2) + "\n", "utf8");
      }
    } catch {
      /* ignore */
    }
  }
  const decisionTpl = join(TEMPLATE, "fri-decision", "decision.json");
  const decisionOut = join(root, "fri-decision", "decision.json");
  if (!existsSync(decisionOut) && existsSync(decisionTpl)) {
    copyFileSync(decisionTpl, decisionOut);
  }
  return root;
}

function updateManifesto(weekRoot, patch) {
  const path = join(weekRoot, "manifesto.json");
  const doc = JSON.parse(readFileSync(path, "utf8"));
  Object.assign(doc, patch);
  if (patch.stage) {
    doc.stages = doc.stages || {};
    if (!doc.stages[patch.stage]) {
      doc.stages[patch.stage] = { status: "pending" };
    }
    Object.assign(doc.stages[patch.stage], patch.stage_patch || {});
  }
  doc.updated_at = new Date().toISOString();
  writeFileSync(path, JSON.stringify(doc, null, 2) + "\n", "utf8");
  return doc;
}

function copyLatest(src, destDir, name) {
  if (!existsSync(src)) return null;
  mkdirSync(destDir, { recursive: true });
  const dest = join(destDir, name);
  cpSync(src, dest, { recursive: true });
  return dest;
}

function runMon(weekRoot, weekId) {
  runNode("scripts/ops/improvement/index-evidence.mjs");
  runNode("scripts/ops/improvement/analyze-evidence.mjs");
  runNode("scripts/ops/v8/pattern-detect.mjs", ["--week-id", weekId, "--weeks", "4"]);
  const analysis = join(REPO, "development", "analysis", "miss", "latest.json");
  copyLatest(analysis, join(weekRoot, "mon-analyzer"), "miss-latest.json");
  const taxonomy = loadTaxonomy();
  writeFileSync(
    join(weekRoot, "mon-analyzer", "taxonomy-ref.json"),
    JSON.stringify(
      {
        schema_version: "expect-v8-analyzer-day/1.0",
        week_id: weekId,
        taxonomy_schema: taxonomy.schema_version,
        family_ids: (taxonomy.families || []).map((f) => f.id),
        note: "V8.1 multi Root Cause + scores. Production miss_category unchanged.",
      },
      null,
      2
    ) + "\n",
    "utf8"
  );
  updateManifesto(weekRoot, {
    stage: "mon_analyzer",
    stage_patch: { status: "completed", at: new Date().toISOString() },
  });
}

function runTue(weekRoot, weekId, phase = "all") {
  const runProposal = phase === "all" || phase === "proposal";
  const runValidation = phase === "all" || phase === "validation";

  if (runProposal) {
    runNode("scripts/ops/improvement/propose-evidence.mjs");
    runNode("scripts/ops/v8/rank-proposals.mjs", ["--week-id", weekId]);
    const proposals = join(REPO, "development", "proposals");
    copyLatest(proposals, join(weekRoot, "tue-proposal"), "proposals-snapshot");
    updateManifesto(weekRoot, {
      stage: "tue_proposal",
      stage_patch: { status: "completed", at: new Date().toISOString() },
    });
  }

  if (runValidation) {
    runNode("scripts/ops/v8/proposal-validate.mjs", ["--week-id", weekId]);
    updateManifesto(weekRoot, {
      stage: "tue_validation",
      stage_patch: { status: "completed", at: new Date().toISOString() },
    });
  }
}

function runWed(weekRoot, weekId) {
  runNode("scripts/ops/v8/canary-ranked.mjs", ["--week-id", weekId]);
  copyLatest(
    join(REPO, "development", "canary"),
    join(weekRoot, "wed-canary"),
    "canary-snapshot"
  );
  writeFileSync(
    join(weekRoot, "wed-canary", "feature-flags-reserved.json"),
    JSON.stringify(
      {
        schema_version: "expect-v8-canary-flags/1.0",
        defaults_off: [
          "v8_canary_candidate_pool",
          "v8_canary_repick",
          "v8_canary_delete",
          "v8_canary_confidence",
          "v8_production_canary",
        ],
        note: "Flags reserved OFF. Canary order = Proposal Ranking priority.",
      },
      null,
      2
    ) + "\n",
    "utf8"
  );
  updateManifesto(weekRoot, {
    stage: "wed_canary",
    stage_patch: { status: "completed", at: new Date().toISOString() },
  });
}

function runThu(weekRoot) {
  runNode("scripts/ops/v8/baseline-285r.mjs", ["--week-root", weekRoot]);
  updateManifesto(weekRoot, {
    stage: "thu_baseline",
    stage_patch: { status: "completed", at: new Date().toISOString() },
  });
}

function runFri(weekRoot, weekId, phase = "all") {
  const runDecision = phase === "all" || phase === "decision";
  const runKnowledge = phase === "all" || phase === "knowledge";
  const runGovernance = phase === "all" || phase === "governance";
  const runReport = phase === "all" || phase === "report";

  if (runDecision) {
    runNode("scripts/ops/v8/decide.mjs", ["--week-id", weekId, "--week-root", weekRoot]);
    updateManifesto(weekRoot, {
      stage: "fri_decision",
      stage_patch: { status: "completed", at: new Date().toISOString() },
    });
    // Deploy-note only — never apply to Production
    writeDeployNoteOnly(weekRoot);
  }

  if (runKnowledge) {
    runNode("scripts/ops/v8/analyzer-feedback.mjs", ["--week-id", weekId]);
    runNode("scripts/ops/v8/knowledge-base.mjs", ["--week-id", weekId]);
    updateManifesto(weekRoot, {
      stage: "fri_knowledge",
      stage_patch: { status: "completed", at: new Date().toISOString() },
    });
  }

  if (runGovernance) {
    runNode("scripts/ops/v8/governance.mjs", ["--week-id", weekId]);
    updateManifesto(weekRoot, {
      stage: "fri_governance",
      stage_patch: { status: "completed", at: new Date().toISOString() },
    });
  }

  if (runReport) {
    runNode("scripts/ops/v8/research-metrics.mjs", ["--week-id", weekId]);
    runNode("scripts/ops/v8/weekly-report.mjs", ["--week-id", weekId]);
    updateManifesto(weekRoot, {
      stage: "fri_report",
      stage_patch: { status: "completed", at: new Date().toISOString() },
    });
    // Keep fri_decision stage marker for older tools
    updateManifesto(weekRoot, {
      stage: "fri_decision",
      stage_patch: { status: "completed", at: new Date().toISOString(), report_done: true },
    });
  }
}

/** Accept でも Production 適用禁止 — deploy-note のみ。 */
function writeDeployNoteOnly(weekRoot) {
  const decisionPath = join(weekRoot, "fri-decision", "decision.json");
  if (!existsSync(decisionPath)) return;
  const decision = JSON.parse(readFileSync(decisionPath, "utf8"));
  const out = join(weekRoot, "sat-deploy", "deploy-note.json");
  mkdirSync(join(weekRoot, "sat-deploy"), { recursive: true });
  const accept =
    decision.decision === "accept" && decision.promote_to_production === true;
  writeFileSync(
    out,
    JSON.stringify(
      {
        schema_version: "expect-v8-deploy-note/1.0",
        ok: true,
        action: accept ? "deploy_note_only_no_auto_apply" : "skip_hold_version",
        week_id: decision.week_id,
        decision: decision.decision,
        promote_to_production: false,
        production_auto_apply: false,
        note: accept
          ? "Accept でも自動 Production 適用禁止。deploy-note のみ。人手 Review 必須。"
          : "改善なし / Reject は成功。Production Version 維持。",
        proposal_ids: decision.proposal_ids || [],
      },
      null,
      2
    ) + "\n",
    "utf8"
  );
  updateManifesto(weekRoot, {
    stage: "sat_deploy",
    stage_patch: {
      status: accept ? "note_only" : "skipped_hold",
      at: new Date().toISOString(),
    },
  });
}

function runSatDeploy(weekRoot) {
  const decisionPath = join(weekRoot, "fri-decision", "decision.json");
  if (!existsSync(decisionPath)) {
    throw new Error("fri-decision/decision.json missing — run v8:fri first");
  }
  const decision = JSON.parse(readFileSync(decisionPath, "utf8"));
  const out = join(weekRoot, "sat-deploy", "deploy-note.json");
  if (decision.decision === "accept" && decision.promote_to_production) {
    writeFileSync(
      out,
      JSON.stringify(
        {
          schema_version: "expect-v8-deploy-note/1.0",
          ok: true,
          action: "deploy_approved_rc",
          week_id: decision.week_id,
          proposal_ids: decision.proposal_ids || [],
          instructions: [
            "Human Review 済み RC のみデプロイ",
            "PE/CE 直接編集禁止 — 承認済み差分 PR のみ",
            "Feature Flag は段階的 ON",
          ],
        },
        null,
        2
      ) + "\n",
      "utf8"
    );
    updateManifesto(weekRoot, {
      stage: "sat_deploy",
      stage_patch: { status: "ready", at: new Date().toISOString() },
    });
  } else {
    writeFileSync(
      out,
      JSON.stringify(
        {
          schema_version: "expect-v8-deploy-note/1.0",
          ok: true,
          action: "skip_hold_version",
          week_id: decision.week_id,
          decision: decision.decision,
          reason: decision.reason,
          note: "改善なし / Reject は成功。Production Version 維持。",
        },
        null,
        2
      ) + "\n",
      "utf8"
    );
    updateManifesto(weekRoot, {
      stage: "sat_deploy",
      stage_patch: { status: "skipped_hold", at: new Date().toISOString() },
    });
  }
}

function main() {
  const day = String(arg("--day", "") || "").toLowerCase();
  const phase = String(arg("--phase", "all") || "all").toLowerCase();
  const allowWeekend = hasFlag("--allow-weekend");
  if (!day) {
    console.error(
      "Usage: run-day.mjs --day mon|tue|wed|thu|fri|sat-deploy|week [--phase proposal|validation|decision|knowledge|governance|report]"
    );
    process.exit(2);
  }

  // Version8.8 — Approval Timeout audit (also on 03:00 runner)
  let approvalExpire = { expired_count: 0 };
  try {
    approvalExpire = expireOverdueApprovals({ now: new Date() });
  } catch (e) {
    console.error(
      JSON.stringify({
        event: "approval_expire_error",
        error: String(e && e.message ? e.message : e),
      })
    );
  }

  if (day !== "sat-deploy") {
    assertResearchDay({
      allowWeekend,
      purpose: `v8:${day}`,
    });
  } else {
    const parts = jstParts();
    if (parts.weekday === 0 && !allowWeekend) {
      assertResearchDay({ allowWeekend: false, purpose: "v8:sat-deploy" });
    }
  }

  const weekId = arg("--week-id", weekIdJst());
  const weekRoot = ensureWeekDir(weekId);
  console.log(
    JSON.stringify(
      {
        event: "v8_day_start",
        day,
        phase,
        week_id: weekId,
        week_root: weekRoot,
        approval_expire: approvalExpire,
      },
      null,
      2
    )
  );

  if (day === "mon") runMon(weekRoot, weekId);
  else if (day === "tue") runTue(weekRoot, weekId, phase);
  else if (day === "wed") runWed(weekRoot, weekId);
  else if (day === "thu") runThu(weekRoot);
  else if (day === "fri") runFri(weekRoot, weekId, phase);
  else if (day === "sat-deploy") runSatDeploy(weekRoot);
  else if (day === "week") {
    runMon(weekRoot, weekId);
    runTue(weekRoot, weekId, "all");
    runWed(weekRoot, weekId);
    runThu(weekRoot);
    runFri(weekRoot, weekId, "all");
  } else {
    console.error(`Unknown day: ${day}`);
    process.exit(2);
  }

  console.log(
    JSON.stringify(
      { event: "v8_day_done", day, phase, week_id: weekId, ok: true },
      null,
      2
    )
  );
}

try {
  main();
} catch (e) {
  console.error(e && e.message ? e.message : e);
  process.exit(e && e.code === "V8_RESEARCH_WEEKEND_BLOCKED" ? 3 : 1);
}
