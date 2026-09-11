-- Isolated live-shaped schema reconstructed from Owner inventory + 001_init / 005.
-- NOT Production SQL files 019_final / 020 / 021 (those stems are not in git).
-- Predictions columns and index match Owner return exactly.
-- Do not apply this file to Production.

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  race_id TEXT NOT NULL,
  core_race_id TEXT,
  engine_source TEXT NOT NULL,
  fallback_reason TEXT,
  model_version TEXT,
  bundle_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_predictions_race ON predictions(race_id, created_at);

CREATE TABLE IF NOT EXISTS conversation_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  intent TEXT,
  race_id TEXT,
  meta_json TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_history(session_id, created_at);

CREATE TABLE IF NOT EXISTS race_results (
  race_id TEXT PRIMARY KEY,
  race_date TEXT NOT NULL,
  venue TEXT,
  meeting_id TEXT,
  surface TEXT,
  distance INTEGER,
  going TEXT,
  winner_horse_number INTEGER,
  field_size INTEGER,
  result_json TEXT,
  source TEXT,
  finalized_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS race_evaluations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER,
  race_id TEXT NOT NULL,
  prediction_id INTEGER,
  race_date TEXT,
  venue TEXT,
  hit_at_1 INTEGER NOT NULL DEFAULT 0,
  hit_at_3 INTEGER NOT NULL DEFAULT 0,
  hit_at_5 INTEGER NOT NULL DEFAULT 0,
  miss_category TEXT,
  engine_source TEXT,
  model_version TEXT,
  evaluated_at TEXT NOT NULL,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS final_predictions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  race_id TEXT,
  payload_json TEXT,
  created_at TEXT
);
