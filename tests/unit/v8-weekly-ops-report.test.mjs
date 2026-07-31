/**
 * Ops weekly report + Incident detect — Version8.5 Operations Mode
 */
import test from "node:test";
import assert from "node:assert/strict";
import {
  BASELINE_LOCK,
  buildBaselineHealthCheck,
  buildWeeklyOpsReport,
} from "../../scripts/ops/v8/weekly-report.mjs";
import { detectIncidents } from "../../scripts/ops/v8/incident-detect.mjs";
import { repoRoot } from "../../scripts/ops/v8/calendar.mjs";
import { join } from "node:path";

test("BASELINE_LOCK is 8.5", () => {
  assert.equal(BASELINE_LOCK, "8.5");
});

test("health check flags production canary OFF as 無", () => {
  const h = buildBaselineHealthCheck({
    REPO: repoRoot(),
    weekRoot: join(repoRoot(), "development", "weekly", "2026-W30"),
    miss: { event_count: 1 },
    baseline: { comparison: { pe_mutated: false } },
    knowledgeSync: {},
    governance: {},
    beta: {
      ui_features: {
        v8_canary_candidate_pool: false,
        v8_canary_repick: false,
        v8_canary_delete: false,
        v8_canary_confidence: false,
        v8_production_canary: false,
      },
    },
  });
  assert.equal(h.pe_changed, "無");
  assert.equal(h.ce_changed, "無");
  assert.equal(h.ai_changed, "無");
  assert.equal(h.feature_flag_mis_on, "無");
  assert.equal(h.production_canary_leak, "無");
  assert.equal(h.baseline_lock, "Version8.5");
  assert.equal(h.miss_evidence, "OK");
});

test("weekly report includes baseline_health and operations_mode", () => {
  const doc = buildWeeklyOpsReport({ week_id: "2026-W30" });
  assert.equal(doc.baseline_version, "8.5");
  assert.equal(doc.operations_mode, true);
  assert.ok(doc.baseline_health);
  assert.equal(doc.baseline_health.baseline_lock, "Version8.5");
  assert.equal(doc.decision.value, "no_improvement");
  assert.equal(doc.decision.ok, true);
  assert.equal(doc.decision.no_improvement_is_success, true);
  assert.equal(doc.safety.pe_ce_ai_unchanged, true);
  assert.equal(doc.safety.new_research_features, false);
});

test("no incident on healthy Sunday ops snapshot", () => {
  const doc = buildWeeklyOpsReport({ week_id: "2026-W30" });
  const { has_incident, incidents } = detectIncidents(doc, null);
  assert.equal(has_incident, false);
  assert.equal(incidents.length, 0);
});

test("incident fires on Miss Evidence NG", () => {
  const { has_incident, incidents } = detectIncidents(
    {
      week_id: "2026-W30",
      generated_at: "2026-07-26T00:00:00.000Z",
      research_ran: false,
      baseline_health: {
        result_automation: "OK",
        miss_evidence: "NG",
        pe_changed: "無",
        feature_flag_mis_on: "無",
        production_canary_leak: "無",
      },
      production: {},
      improvement: { vs_prev_week: {} },
    },
    null
  );
  assert.equal(has_incident, true);
  assert.ok(incidents.some((i) => i.code === "MISS_EVIDENCE_MISSING"));
  assert.ok(incidents[0].occurred_at);
  assert.ok(incidents[0].scope);
  assert.ok(incidents[0].cause_candidates?.length);
  assert.ok(incidents[0].recommended_action);
  assert.equal(typeof incidents[0].production_impact, "boolean");
});
