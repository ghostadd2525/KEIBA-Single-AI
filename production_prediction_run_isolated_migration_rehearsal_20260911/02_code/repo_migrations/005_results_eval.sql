-- Phase P-1 / STATS — race results & evaluations (Production only)
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

CREATE INDEX IF NOT EXISTS idx_race_results_date ON race_results(race_date);

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

CREATE INDEX IF NOT EXISTS idx_race_evaluations_date ON race_evaluations(race_date);

CREATE TABLE IF NOT EXISTS self_evaluation_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  race_date TEXT,
  trigger_source TEXT,
  status TEXT NOT NULL,
  races_evaluated INTEGER DEFAULT 0,
  hits INTEGER DEFAULT 0,
  misses INTEGER DEFAULT 0,
  hit_at_1_rate REAL,
  hit_at_3_rate REAL,
  hit_at_5_rate REAL,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  finished_at TEXT
);
