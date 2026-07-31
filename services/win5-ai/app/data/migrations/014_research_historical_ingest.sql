-- Version11.1 Research Historical Bundle Ingest
-- Research-only. Does NOT mutate Product predictions / PE / CE / AI.

CREATE TABLE IF NOT EXISTS research_historical_bundles (
  ingest_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  source_path TEXT,
  race_id TEXT NOT NULL,
  race_date TEXT,
  venue TEXT,
  surface TEXT,
  distance INTEGER,
  class_label TEXT,
  race_name TEXT,
  has_bundle INTEGER NOT NULL DEFAULT 0,
  has_model_rank INTEGER NOT NULL DEFAULT 0,
  has_race_result INTEGER NOT NULL DEFAULT 0,
  has_winner INTEGER NOT NULL DEFAULT 0,
  tie_eligible INTEGER NOT NULL DEFAULT 0,
  tie_size INTEGER,
  winner_horse_number INTEGER,
  winner_horse_id TEXT,
  runner_count INTEGER,
  validation_status TEXT NOT NULL,
  validation_errors_json TEXT,
  bundle_json TEXT,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_research_hist_bundles_race_source
  ON research_historical_bundles(race_id, source);

CREATE INDEX IF NOT EXISTS idx_research_hist_bundles_flags
  ON research_historical_bundles(has_bundle, tie_eligible, validation_status);

CREATE TABLE IF NOT EXISTS research_unrecoverable_predictions (
  record_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  race_id TEXT NOT NULL,
  reason TEXT NOT NULL,
  has_metadata INTEGER NOT NULL DEFAULT 1,
  meta_json TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_unrecoverable_race
  ON research_unrecoverable_predictions(race_id, source);

CREATE TABLE IF NOT EXISTS research_ingest_runs (
  run_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  inventory_json TEXT,
  summary_json TEXT,
  created_at TEXT NOT NULL
);
