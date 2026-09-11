-- Migration: 022_prediction_run_idempotency
-- Isolated rehearsal copy. Do not apply to Production from this pack.
-- Adds four nullable columns and a partial UNIQUE index.
-- Live Owner inventory confirms these objects are absent and do not collide.

ALTER TABLE predictions ADD COLUMN idempotency_key TEXT;
ALTER TABLE predictions ADD COLUMN persist_source TEXT;
ALTER TABLE predictions ADD COLUMN input_snapshot_hash TEXT;
ALTER TABLE predictions ADD COLUMN prediction_semantic_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_predictions_idempotency_key_not_null
  ON predictions(idempotency_key)
  WHERE idempotency_key IS NOT NULL;
