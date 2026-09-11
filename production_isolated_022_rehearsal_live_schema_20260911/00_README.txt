Isolated 022 rehearsal on Owner live schema inventory
=====================================================

PACK=production_isolated_022_rehearsal_live_schema_20260911

Owner inventory is canonical. Live predictions are 8 columns plus
idx_predictions_race. persist 019/022 are absent. 022 four columns and
the partial UNIQUE index do not collide.

This pack builds a temp DB from that live shape, then applies 022 via
the standalone migrate/repair copy. Production is never opened.

Confirmed
  first apply
  second migrate no-op
  partial index repair
  existing 300 NULL-row compatibility
  Conversation / RA / Challenge legacy INSERT (new cols stay NULL)
  rollback: unset EXPECT_AI_ALLOW_MIGRATION_022 then DROP INDEX stays dropped

Not done
  Production backup
  Production APPLY
  HTTP / GET / UI / Conversation service / win_prob/model_rank/mark changes
  PREDICTION_RUNS_ENABLED=1

Re-run: python3 run_tests.py
