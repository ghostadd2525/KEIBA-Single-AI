-- Migration: 007_collect_c0
-- Collector C-0 — collect_targets / collect_jobs / collect_artifacts / collect_runs

CREATE TABLE IF NOT EXISTS collect_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  planner_run_id TEXT NOT NULL UNIQUE,
  week_id TEXT NOT NULL,
  calendar_version TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'running',
  targets_count INTEGER NOT NULL DEFAULT 0,
  jobs_enqueued INTEGER NOT NULL DEFAULT 0,
  manifest_path TEXT,
  detail_json TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_collect_runs_week
  ON collect_runs(week_id, started_at DESC);

CREATE TABLE IF NOT EXISTS collect_targets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  planner_run_id TEXT NOT NULL,
  week_id TEXT NOT NULL,
  calendar_version TEXT NOT NULL,
  race_date TEXT NOT NULL,
  venue TEXT NOT NULL,
  race_no INTEGER NOT NULL,
  race_id TEXT,
  public_race_id TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(planner_run_id) REFERENCES collect_runs(planner_run_id),
  UNIQUE(week_id, race_date, venue, race_no)
);

CREATE INDEX IF NOT EXISTS idx_collect_targets_week
  ON collect_targets(week_id, race_date, venue, race_no);

CREATE INDEX IF NOT EXISTS idx_collect_targets_planner
  ON collect_targets(planner_run_id);

CREATE TABLE IF NOT EXISTS collect_artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  artifact_uid TEXT NOT NULL UNIQUE,
  job_id TEXT NOT NULL,
  week_id TEXT NOT NULL,
  race_date TEXT NOT NULL,
  race_id TEXT,
  artifact_type TEXT NOT NULL,
  kind TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  raw_path TEXT,
  content_hash TEXT,
  validation_errors_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_collect_artifacts_week
  ON collect_artifacts(week_id, status);

CREATE INDEX IF NOT EXISTS idx_collect_artifacts_job
  ON collect_artifacts(job_id);

CREATE TABLE IF NOT EXISTS collect_jobs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL UNIQUE,
  planner_run_id TEXT,
  target_id INTEGER,
  week_id TEXT NOT NULL,
  race_date TEXT NOT NULL,
  race_id TEXT,
  artifact_type TEXT NOT NULL,
  kind TEXT NOT NULL,
  priority TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'PENDING',
  budget_cost INTEGER NOT NULL DEFAULT 1,
  attempt INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 5,
  scheduled_for TEXT,
  retry_after TEXT,
  last_error TEXT,
  artifact_id INTEGER,
  validation_errors_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY(planner_run_id) REFERENCES collect_runs(planner_run_id),
  FOREIGN KEY(target_id) REFERENCES collect_targets(id),
  FOREIGN KEY(artifact_id) REFERENCES collect_artifacts(id)
);

CREATE INDEX IF NOT EXISTS idx_collect_jobs_week_status
  ON collect_jobs(week_id, status, priority, scheduled_for);

CREATE INDEX IF NOT EXISTS idx_collect_jobs_target
  ON collect_jobs(target_id);
