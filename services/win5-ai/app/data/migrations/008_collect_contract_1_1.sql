-- Migration: 008_collect_contract_1_1
-- Collector Contract 1.1 — idempotency + scheduler dequeue index

-- Must-2: Job idempotency
-- Adopted key: (week_id, target_id, artifact_type)
-- Rationale:
--   * target_id uniquely identifies (race_date, venue, race_no) within a week via collect_targets.
--   * race_id is often NULL at Planner enqueue time; SQLite UNIQUE treats each NULL as distinct,
--     so (week_id, race_date, race_id, artifact_type) would NOT prevent duplicate enqueues.
--   * artifact_type distinguishes race_meta / entries_core / odds etc. on the same target.
-- Planner MUST set target_id when enqueueing jobs (Contract 1.1).

CREATE UNIQUE INDEX IF NOT EXISTS uq_collect_jobs_week_target_artifact
  ON collect_jobs(week_id, target_id, artifact_type);

-- Must-3: Scheduler dequeue — aligns with design ORDER BY:
--   priority ASC, kind (CORE→PROFILE→HISTORY), scheduled_for ASC, attempt ASC, job_id ASC
CREATE INDEX IF NOT EXISTS idx_collect_jobs_dequeue
  ON collect_jobs(week_id, status, priority, kind, scheduled_for, attempt, job_id);
