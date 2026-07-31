-- Version19 Research Knowledge Validation Lab
-- Research / Shadow only. Does NOT mutate Prediction / PE / CE / AI /
-- Challenge / Resolver / ResultAutomation / Production.

CREATE TABLE IF NOT EXISTS research_knowledge_states (
  knowledge_id TEXT PRIMARY KEY,
  state TEXT NOT NULL,
  recommended_action TEXT,
  updated_at TEXT NOT NULL,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS research_shadow_feature_flags (
  flag_id TEXT PRIMARY KEY,
  knowledge_id TEXT NOT NULL,
  flag_key TEXT NOT NULL UNIQUE,
  flag_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_shadow_flags_knowledge
  ON research_shadow_feature_flags(knowledge_id);

CREATE TABLE IF NOT EXISTS research_knowledge_validation_runs (
  run_id TEXT PRIMARY KEY,
  week_id TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  summary_json TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_knowledge_validations (
  validation_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  knowledge_id TEXT NOT NULL,
  shadow_flag_id TEXT,
  metrics_json TEXT NOT NULL,
  governance_json TEXT NOT NULL,
  passed INTEGER NOT NULL DEFAULT 0,
  state_before TEXT NOT NULL,
  state_after TEXT NOT NULL,
  knowledge_drift REAL,
  rank_score REAL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_knowledge_validations_run
  ON research_knowledge_validations(run_id, passed);

CREATE TABLE IF NOT EXISTS research_knowledge_validation_history (
  history_id TEXT PRIMARY KEY,
  knowledge_id TEXT NOT NULL,
  run_id TEXT NOT NULL,
  week_id TEXT NOT NULL,
  event TEXT NOT NULL,
  state_before TEXT,
  state_after TEXT,
  detail_json TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_validation_history_knowledge
  ON research_knowledge_validation_history(knowledge_id, created_at);
