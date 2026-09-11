-- Version16 Research Metadata Completion
-- Research-only. Does NOT mutate Product predictions / PE / CE / AI /
-- Challenge / Resolver / ResultAutomation.

CREATE TABLE IF NOT EXISTS research_race_meta (
  race_id TEXT PRIMARY KEY,
  surface TEXT,
  distance INTEGER,
  field_size INTEGER,
  age_group TEXT,
  weather TEXT,
  going TEXT,
  race_class TEXT,
  course_type TEXT,
  class_label TEXT,
  venue TEXT,
  race_date TEXT,
  numeric_race_id TEXT,
  source_chain_json TEXT NOT NULL,
  completeness REAL NOT NULL DEFAULT 0,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_race_meta_cov
  ON research_race_meta(surface, going, weather, age_group);

CREATE TABLE IF NOT EXISTS research_metadata_runs (
  run_id TEXT PRIMARY KEY,
  schema_version TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  coverage_before_json TEXT,
  coverage_after_json TEXT,
  summary_json TEXT,
  created_at TEXT NOT NULL
);
