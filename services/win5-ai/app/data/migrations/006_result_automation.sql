-- Phase OPS-ResultAutomation — runs + evidence index
CREATE TABLE IF NOT EXISTS result_automation_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  race_date TEXT NOT NULL,
  status TEXT NOT NULL,
  trigger TEXT NOT NULL,
  parent_run_id INTEGER,
  attempt INTEGER NOT NULL DEFAULT 1,
  max_attempts INTEGER NOT NULL DEFAULT 5,
  started_at TEXT,
  finished_at TEXT,
  error_json TEXT,
  meta_json TEXT,
  self_eval_run_id INTEGER,
  FOREIGN KEY (parent_run_id) REFERENCES result_automation_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_ra_runs_date_status
  ON result_automation_runs(race_date, status);

CREATE TABLE IF NOT EXISTS improvement_evidence_index (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  race_id TEXT,
  race_date TEXT NOT NULL,
  fingerprint TEXT,
  path TEXT NOT NULL,
  run_id INTEGER NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ie_index_date_type
  ON improvement_evidence_index(race_date, event_type);
