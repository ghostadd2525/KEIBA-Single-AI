-- Version10.1 — denormalized feature / quality tables for harvest ops
-- Linked to research_prediction_snapshots by snapshot_id / prediction_id

CREATE TABLE IF NOT EXISTS research_snapshot_features (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  snapshot_id TEXT NOT NULL,
  prediction_id INTEGER NOT NULL,
  race_id TEXT NOT NULL,
  horse_number INTEGER NOT NULL,
  feature_id TEXT NOT NULL,
  value_json TEXT,
  source_id TEXT,
  observed_at TEXT,
  missing_reason TEXT,
  asof_clamped INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  UNIQUE(snapshot_id, horse_number, feature_id)
);

CREATE INDEX IF NOT EXISTS idx_research_snapshot_features_pred
  ON research_snapshot_features(prediction_id, feature_id);

CREATE TABLE IF NOT EXISTS research_snapshot_quality (
  snapshot_id TEXT PRIMARY KEY,
  prediction_id INTEGER NOT NULL UNIQUE,
  race_id TEXT NOT NULL,
  capture_status TEXT NOT NULL,
  field_coverage REAL,
  completeness REAL,
  consistency REAL,
  anti_leak_violations INTEGER NOT NULL DEFAULT 0,
  asof_clamped INTEGER NOT NULL DEFAULT 0,
  runner_count INTEGER NOT NULL DEFAULT 0,
  feature_fill_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
