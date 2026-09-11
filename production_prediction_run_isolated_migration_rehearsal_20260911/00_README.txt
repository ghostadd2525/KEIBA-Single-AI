Step 5 isolated current-schema migration rehearsal
=================================================

PACK=production_prediction_run_isolated_migration_rehearsal_20260911
THIS IS NOT APPLY.
PRODUCTION_APPLY_READY=NO
OWNER_APPLY_APPROVED=NO

Owner DRY_RUN 正本
  OUTPUT_SHA256=6f0901221eaa625c51976d5ce6aae110175732a1cd7dfd846c6d774a24f66862
  OWNER_AUDIT_IMPORTED=YES
  AUDIT_STATUS=SUCCESS
  DISABLED_POST_DRY_RUN_COMPLETE=YES
  CURRENT_PRODUCTION_BASELINE_COMPLETE=YES_EXCEPT_CURRENT_DAY
  CURRENT_DAY_DATA_VERIFIED=NO_RESEARCH_WEEK
  PRODUCTION_CHANGED=NO
  DB_CHANGED=NO

このパックは Production を開かない。
現行 live schema 相当（001〜018 + 019_final_predictions stub + 020/021 stub）
を隔離 temp DB に構築し、承認済みローカル実装の migrate() で
019_prediction_run_idempotency を適用する。

実行（このワークスペースのみ）
  python3 run_tests.py

禁止
  Production SSH / DB copy / env / systemd 変更
  EXPECT_AI_ALLOW_MIGRATION_019 を Production で有効化
  Production へ 019 適用
  POST /v1/prediction-runs を Production で有効化・呼び出し
  既存 review ZIP / DRY_RUN ZIP の上書き
  PR #23 / #24 / #25 の更新

APPLY にしない理由（正本 blocker のまま）
  BLOCKER_1 SQLITE3_CLI_PRESENT=NO → DB_BACKUP_POSSIBLE=NO
  BLOCKER_2 Conversation / RA / Challenge の Production 実書込みは未実行
  本パックの書込み確認は隔離 DB / ローカル service fixture のみ
