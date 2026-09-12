-- Migration: 019_prediction_run_idempotency
-- Adds nullable idempotency columns and a partial UNIQUE index.
-- PredictionRepository.save leaves these columns NULL (legacy multi-row OK).
-- Do not apply this file to Production from this local-only change.

ALTER TABLE predictions ADD COLUMN idempotency_key TEXT;
ALTER TABLE predictions ADD COLUMN persist_source TEXT;
ALTER TABLE predictions ADD COLUMN input_snapshot_hash TEXT;
ALTER TABLE predictions ADD COLUMN prediction_semantic_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_predictions_idempotency_key_not_null
  ON predictions(idempotency_key)
  WHERE idempotency_key IS NOT NULL;
