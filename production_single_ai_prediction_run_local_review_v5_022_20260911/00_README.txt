Local review v5 — persist apply target rebased to 022
===================================================

PACK=production_single_ai_prediction_run_local_review_v5_022_20260911
THIS IS NOT APPLY.
v1-v4 review ZIP は上書きしない。
旧 019 persist SQL は migrations_not_apply に byte-identical で保持。

Apply target
  022_prediction_run_idempotency
  gate: EXPECT_AI_ALLOW_MIGRATION_022
  sorts after live 019_final_predictions / 020 / 021

Superseded
  019_prediction_run_idempotency
  SHA256=d8fc71e316d7819a4dcfc0977bf6444308410144b62fd29a33ca764ea853370f
  migrate() skips this stem even if someone puts the file back

PRODUCTION_APPLY_READY=NO
OWNER_APPLY_APPROVED=NO
Production に 019 も 022 も適用しない。
