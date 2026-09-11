Step 2-4 Owner read-only / DRY_RUN pack
=======================================

PACK=production_prediction_run_baseline_disabled_post_dry_run_readonly_20260911
SCOPE=PRODUCTION_BASELINE + 019_UNAPPLIED + POST_DISABLED_DRY_RUN + GET/Conversation/RA/Challenge regression
THIS IS NOT APPLY.

固定順序のうち Step 2〜4 だけ:
  2. 現行 Production baseline を read-only 再確認
  3. 019 未適用・PREDICTION_RUNS_ENABLED=0 を確認（POST は呼ばない）
  4. GET / Conversation / RA / Challenge の既存挙動を回帰確認

この pack は Owner が EC2 で実行する。Cursor は Production に接続しない。

禁止（この段階）
  EXPECT_AI_ALLOW_MIGRATION_019 を有効化しない
  019 を適用しない
  POST を有効化しない
  POST /v1/prediction-runs を呼ばない（503 確認のための POST も不可）
  DB / env / systemd / GitHub / PR #23 を変更しない
  過去 race で live 推論しない（detail GET しない）
  Production bundle を APPLY しない
  既存 v1〜v4 review ZIP を上書きしない
  v1 prediction-path smoke を実行しない

許可 HTTP（remote loopback のみ）
  GET http://127.0.0.1:8000/health
  GET http://127.0.0.1:8000/v1/predictions
    AI_ENGINE=real のときは ?date=2099-01-01 のみ（空一覧。live 推論しない）
  Conversation / Challenge の write HTTP はしない
  RA run / Challenge monthly GET はしない（settle / INSERT し得る）

実行
  02_powershell\OWNER_READONLY.ps1

出力
  C:\Users\Mr.me\Downloads\production_prediction_run_baseline_disabled_post_dry_run_readonly_20260911_output_<ts>.txt

判定
  この pack の作成とローカル試験 PASS は PRODUCTION_DRY_RUN_READY=YES ではない。
  Owner が実行し、結果を返すまで PRODUCTION_DRY_RUN_READY=NO。
  PRODUCTION_APPLY_READY=NO
  OWNER_APPLY_APPROVED=NO
  APPLY_EXECUTED=NO
