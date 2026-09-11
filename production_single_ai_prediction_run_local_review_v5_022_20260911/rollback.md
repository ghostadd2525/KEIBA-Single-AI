Rollback（022 / POST persist）v5

目的: uniqueness と POST 入口だけを止める。予測行は残す。

必須順（019 時代と同じ失敗を防ぐ）
  1. PREDICTION_RUNS_ENABLED=0
  2. EXPECT_AI_ALLOW_MIGRATION_022 を解除
  3. EXPECT_AI_ALLOW_MIGRATION_019 も解除（旧ゲートが残ると将来混乱する）
  4. DROP INDEX IF EXISTS uq_predictions_idempotency_key_not_null
  2 を残すと migrate() が index を再生成する。

しない
  DROP COLUMN
  DELETE FROM predictions
  UPDATE predictions SET bundle_json=...
  Conversation / Challenge / RA INSERT の変更
  旧 019 SQL の再投入

schema_migrations の version は 022_prediction_run_idempotency。
この文書は Production で rollback を実行しない。
