-- Version20 Production Candidate Review
-- Research-only design review. Does NOT mutate Prediction / PE / CE / AI /
-- Challenge / Resolver / ResultAutomation / Production.

CREATE TABLE IF NOT EXISTS research_candidate_reviews (
  review_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL,
  knowledge_id TEXT NOT NULL,
  verdict TEXT NOT NULL,
  dimension_json TEXT NOT NULL,
  risk_json TEXT NOT NULL,
  adoption_json TEXT NOT NULL,
  promote_v21 INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_candidate_reviews_run
  ON research_candidate_reviews(run_id, verdict);

CREATE TABLE IF NOT EXISTS research_candidate_review_runs (
  run_id TEXT PRIMARY KEY,
  week_id TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  summary_json TEXT,
  created_at TEXT NOT NULL
);
