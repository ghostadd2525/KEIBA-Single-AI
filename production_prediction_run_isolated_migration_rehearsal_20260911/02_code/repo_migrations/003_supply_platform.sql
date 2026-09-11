-- Migration: 003_supply_platform
-- ETL runs, import history, validation snapshots

CREATE TABLE IF NOT EXISTS etl_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  race_date TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  source_type TEXT,
  stopped_at_step TEXT,
  error_reason TEXT,
  missing_data_json TEXT,
  result_json TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_etl_runs_date ON etl_runs(race_date, started_at DESC);

CREATE TABLE IF NOT EXISTS etl_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL,
  step TEXT NOT NULL,
  status TEXT NOT NULL,
  detail_json TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  FOREIGN KEY(run_id) REFERENCES etl_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_etl_steps_run ON etl_steps(run_id, id);

CREATE TABLE IF NOT EXISTS import_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER,
  race_date TEXT,
  source_type TEXT,
  races_count INTEGER DEFAULT 0,
  features_count INTEGER DEFAULT 0,
  entries_count INTEGER DEFAULT 0,
  horses_count INTEGER DEFAULT 0,
  skipped_count INTEGER DEFAULT 0,
  detail_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES etl_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_import_history_date ON import_history(race_date, created_at DESC);

CREATE TABLE IF NOT EXISTS validation_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER,
  race_date TEXT,
  race_total INTEGER DEFAULT 0,
  real_ai INTEGER DEFAULT 0,
  mock INTEGER DEFAULT 0,
  coverage REAL DEFAULT 0,
  missing_features INTEGER DEFAULT 0,
  missing_races INTEGER DEFAULT 0,
  by_reason_json TEXT,
  items_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(run_id) REFERENCES etl_runs(id)
);

CREATE INDEX IF NOT EXISTS idx_validation_runs_date ON validation_runs(race_date, created_at DESC);
