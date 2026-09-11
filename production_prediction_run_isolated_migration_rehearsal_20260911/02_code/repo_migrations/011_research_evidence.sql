-- Version10 Research Evidence Platform (Prediction Snapshot store)
-- Isolated from Product predictions; linked by prediction_id only.

CREATE TABLE IF NOT EXISTS research_collect_jobs (
  job_id TEXT PRIMARY KEY,
  prediction_id INTEGER NOT NULL,
  race_id TEXT NOT NULL,
  prediction_created_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempt INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 5,
  priority TEXT NOT NULL DEFAULT 'normal',
  enqueued_at TEXT NOT NULL,
  started_at TEXT,
  finished_at TEXT,
  deadline_at TEXT,
  last_error TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  UNIQUE(prediction_id)
);

CREATE INDEX IF NOT EXISTS idx_research_collect_jobs_status
  ON research_collect_jobs(status, enqueued_at);

CREATE TABLE IF NOT EXISTS research_prediction_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  prediction_id INTEGER NOT NULL UNIQUE,
  race_id TEXT NOT NULL,
  race_date TEXT,
  captured_at TEXT NOT NULL,
  capture_status TEXT NOT NULL,
  field_coverage REAL,
  anti_leak_violations INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL,
  json_path TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_snapshots_race_date
  ON research_prediction_snapshots(race_date, captured_at);

CREATE TABLE IF NOT EXISTS research_source_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL,
  prediction_id INTEGER NOT NULL,
  feature_id TEXT NOT NULL,
  source_id TEXT NOT NULL,
  success INTEGER NOT NULL,
  observed_at TEXT,
  fetched_at TEXT NOT NULL,
  latency_ms REAL,
  missing_reason TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_source_events_job
  ON research_source_events(job_id);

CREATE TABLE IF NOT EXISTS research_evidence_daily (
  metric_date TEXT NOT NULL,
  feature_id TEXT NOT NULL,
  coverage REAL,
  missing_rate REAL,
  freshness_p50_sec REAL,
  completeness REAL,
  consistency REAL,
  success_rate REAL,
  retry_total INTEGER NOT NULL DEFAULT 0,
  source_latency_p50_ms REAL,
  source_availability REAL,
  sample_count INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (metric_date, feature_id)
);
