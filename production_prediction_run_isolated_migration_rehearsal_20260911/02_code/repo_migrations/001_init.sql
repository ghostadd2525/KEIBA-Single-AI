-- Expect AI operational schema (SQLite / PostgreSQL compatible subset)
-- Migration: 001_init

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS races (
  race_id TEXT PRIMARY KEY,
  date TEXT NOT NULL,
  venue TEXT NOT NULL,
  race_no INTEGER NOT NULL,
  meeting_id TEXT,
  surface TEXT,
  distance INTEGER,
  class_label TEXT,
  grade TEXT,
  field_size INTEGER,
  post_time TEXT,
  status TEXT,
  source TEXT,
  extra_json TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_races_date_venue_no ON races(date, venue, race_no);

CREATE TABLE IF NOT EXISTS horses (
  horse_id TEXT PRIMARY KEY,
  horse_name TEXT NOT NULL,
  sex TEXT,
  birth_year INTEGER,
  extra_json TEXT,
  created_at TEXT,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  race_id TEXT NOT NULL,
  horse_id TEXT,
  horse_number INTEGER,
  horse_name TEXT,
  frame_number INTEGER,
  jockey TEXT,
  odds REAL,
  popularity INTEGER,
  extra_json TEXT,
  UNIQUE(race_id, horse_number),
  FOREIGN KEY(race_id) REFERENCES races(race_id)
);

CREATE INDEX IF NOT EXISTS idx_entries_race ON entries(race_id);

CREATE TABLE IF NOT EXISTS features (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  race_id TEXT NOT NULL,
  horse_number INTEGER,
  horse_id TEXT,
  feature_set TEXT NOT NULL DEFAULT 'runners_pace_market',
  payload_json TEXT NOT NULL,
  source_file TEXT,
  created_at TEXT,
  UNIQUE(race_id, horse_number, feature_set)
);

CREATE INDEX IF NOT EXISTS idx_features_race ON features(race_id);

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

CREATE TABLE IF NOT EXISTS logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  level TEXT NOT NULL,
  category TEXT NOT NULL,
  message TEXT NOT NULL,
  race_id TEXT,
  payload_json TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_created ON logs(created_at);

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
