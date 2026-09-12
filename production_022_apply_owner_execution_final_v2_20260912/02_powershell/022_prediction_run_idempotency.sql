-- Embedded review copy. The stdin payload applies the same statements.
-- Do not apply this file with sqlite3 CLI. Owner runs OWNER_APPLY.ps1 only.

ALTER TABLE predictions ADD COLUMN idempotency_key TEXT;
ALTER TABLE predictions ADD COLUMN persist_source TEXT;
ALTER TABLE predictions ADD COLUMN input_snapshot_hash TEXT;
ALTER TABLE predictions ADD COLUMN prediction_semantic_hash TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_predictions_idempotency_key_not_null
  ON predictions(idempotency_key)
  WHERE idempotency_key IS NOT NULL;
