Step 2-4 Owner read-only / DRY_RUN pack v2 (syntax fix only)
===========================================================

PACK=production_prediction_run_baseline_disabled_post_dry_run_readonly_v2_20260911
V1_PACK=production_prediction_run_baseline_disabled_post_dry_run_readonly_20260911
V1_ZIP_SHA256=2930e43193ca8e17abbc4d0ec2eff79090070efc5bc44727e3e16e866e546663
V1_DO_NOT_RUN=YES
V1_PARSE_ERROR=YES
THIS IS NOT APPLY.

v1 OWNER_READONLY.ps1 は PowerShell 構文エラー (MissingCatchOrFinally / closing } mismatch)。
SSH 開始前に停止した。Production 影響なし。
v1 ZIP は変更・上書きしない。remote Python は v1 と同一バイト。

修正
  内側 try { if { ... } } catch { } の閉じ } を復元（stdout/stderr drain）
  外側 try/catch の波括弧対応を Parser.ParseFile で確認

実行
  02_powershell\OWNER_READONLY.ps1

禁止は v1 と同一。019 適用なし。POST なし。detail GET なし。
