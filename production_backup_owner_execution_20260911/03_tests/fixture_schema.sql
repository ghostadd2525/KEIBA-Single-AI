-- Self-contained rehearsal schema. No external repository paths.
-- Does not include live row bodies, race_id values, or horse names.
CREATE TABLE schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL
);
CREATE TABLE predictions (
  id INTEGER PRIMARY KEY,
  engine_source TEXT,
  payload TEXT,
  created_at TEXT
);
CREATE INDEX idx_predictions_created ON predictions(created_at);
CREATE VIEW predictions_count AS SELECT COUNT(*) AS n FROM predictions;
CREATE TRIGGER trg_predictions_touch AFTER INSERT ON predictions
BEGIN
  UPDATE schema_migrations SET applied_at = applied_at WHERE version = '001_init';
END;
INSERT INTO schema_migrations(version, applied_at) VALUES ('001_init', 't');
INSERT INTO predictions(engine_source, payload, created_at) VALUES ('real_ai', 'HIDE', 't');
