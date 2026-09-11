-- Version18 Research Knowledge Base
-- Research-only. Does NOT mutate Product predictions / PE / CE / AI /
-- Challenge / Resolver / Shadow / ResultAutomation.

CREATE TABLE IF NOT EXISTS research_knowledge_entries (
  knowledge_id TEXT PRIMARY KEY,
  knowledge_type TEXT NOT NULL,
  week_id TEXT NOT NULL,
  observation TEXT NOT NULL,
  evidence_json TEXT NOT NULL,
  hypothesis TEXT NOT NULL,
  confidence TEXT NOT NULL,
  limitations_json TEXT NOT NULL,
  recommended_action TEXT NOT NULL,
  graph_json TEXT,
  source_key TEXT,
  meta_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_knowledge_week
  ON research_knowledge_entries(week_id, knowledge_type);

CREATE INDEX IF NOT EXISTS idx_research_knowledge_action
  ON research_knowledge_entries(recommended_action, confidence);

CREATE TABLE IF NOT EXISTS research_knowledge_snapshots (
  snapshot_id TEXT PRIMARY KEY,
  week_id TEXT NOT NULL UNIQUE,
  schema_version TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  entry_count INTEGER NOT NULL,
  snapshot_path TEXT,
  summary_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_knowledge_diffs (
  diff_id TEXT PRIMARY KEY,
  week_id TEXT NOT NULL,
  prev_week_id TEXT,
  added_count INTEGER NOT NULL DEFAULT 0,
  removed_count INTEGER NOT NULL DEFAULT 0,
  changed_count INTEGER NOT NULL DEFAULT 0,
  diff_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_knowledge_diffs_week
  ON research_knowledge_diffs(week_id);
