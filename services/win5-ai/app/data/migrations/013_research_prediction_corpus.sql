-- Version11 Research Prediction Corpus
-- Research-only tables. Does NOT mutate Product predictions / PE / CE / AI.

CREATE TABLE IF NOT EXISTS research_prediction_corpus (
  corpus_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  prediction_id INTEGER,
  race_id TEXT NOT NULL,
  race_date TEXT,
  venue TEXT,
  surface TEXT,
  distance INTEGER,
  class_label TEXT,
  age_group TEXT,
  is_young_horse INTEGER NOT NULL DEFAULT 0,
  is_tie INTEGER NOT NULL DEFAULT 0,
  tie_size INTEGER,
  has_prediction_bundle INTEGER NOT NULL DEFAULT 0,
  has_race_result INTEGER NOT NULL DEFAULT 0,
  has_evidence_snapshot INTEGER NOT NULL DEFAULT 0,
  has_shadow_result INTEGER NOT NULL DEFAULT 0,
  has_governance INTEGER NOT NULL DEFAULT 0,
  winner_horse_number INTEGER,
  prediction_pick INTEGER,
  shadow_pick INTEGER,
  shadow_outcome TEXT,
  snapshot_id TEXT,
  engine_source TEXT,
  completeness REAL,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_prediction_corpus_race
  ON research_prediction_corpus(race_id, race_date);

CREATE INDEX IF NOT EXISTS idx_research_prediction_corpus_flags
  ON research_prediction_corpus(is_tie, is_young_horse, source);

CREATE TABLE IF NOT EXISTS research_tie_corpus (
  corpus_id TEXT PRIMARY KEY,
  race_id TEXT NOT NULL,
  race_date TEXT,
  venue TEXT,
  surface TEXT,
  distance INTEGER,
  class_label TEXT,
  age_group TEXT,
  tie_size INTEGER NOT NULL,
  winner_horse_number INTEGER,
  prediction_pick INTEGER,
  shadow_pick INTEGER,
  shadow_outcome TEXT,
  used_feature TEXT,
  used_tier TEXT,
  confidence REAL,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(corpus_id) REFERENCES research_prediction_corpus(corpus_id)
);

CREATE TABLE IF NOT EXISTS research_young_horse_corpus (
  corpus_id TEXT PRIMARY KEY,
  race_id TEXT NOT NULL,
  race_date TEXT,
  venue TEXT,
  surface TEXT,
  distance INTEGER,
  class_label TEXT,
  age_group TEXT,
  is_tie INTEGER NOT NULL DEFAULT 0,
  tie_size INTEGER,
  winner_horse_number INTEGER,
  prediction_pick INTEGER,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(corpus_id) REFERENCES research_prediction_corpus(corpus_id)
);

CREATE TABLE IF NOT EXISTS research_corpus_runs (
  run_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  prediction_count INTEGER NOT NULL DEFAULT 0,
  tie_count INTEGER NOT NULL DEFAULT 0,
  young_horse_count INTEGER NOT NULL DEFAULT 0,
  target_prediction INTEGER NOT NULL DEFAULT 3000,
  target_tie INTEGER NOT NULL DEFAULT 300,
  target_young_horse INTEGER NOT NULL DEFAULT 300,
  summary_json TEXT,
  created_at TEXT NOT NULL
);
