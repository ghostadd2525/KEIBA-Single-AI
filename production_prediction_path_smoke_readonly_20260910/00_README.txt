Production Single-AI 予想経路 read-only smoke
===========================================

Cursor は Production に SSH しない。公開 BFF の /api/predictions は
Research Week (OPS_CLOSED) のため USER 経路では 503。
内部 Python GET /v1/predictions は EC2 loopback のみ。

本 pack は Owner が 1 回だけ実行する。GET と read-only metadata だけ。
POST /v1/prediction-runs は呼ばない。

実行
  02_powershell\OWNER_READONLY.ps1

固定接続
  PEM=C:\Users\Mr.me\Downloads\expect-beta-tokyo.pem
  TARGET=ubuntu@13.231.5.5
  remote: PYTHONDONTWRITEBYTECODE=1 python3 -
  prediction_smoke_readonly.py は stdin 送信。SCP / remote mkdir / sudo なし。

許可 HTTP（remote のみ）
  GET http://127.0.0.1:8000/health
  GET http://127.0.0.1:8000/v1/predictions
  GET http://127.0.0.1:8000/v1/predictions/{existing_race_id}

禁止
  POST /v1/prediction-runs
  公開 Origin への書込み
  Production ファイル / DB / env / service 変更
  Conversation / Result Automation 変更
  systemctl start|stop|restart|reload|enable|disable
  推測 race_id

race_id 選定
  1. GET 一覧の当日・runners 非空
  2. GET 一覧の runners 非空
  3. GET 一覧の先頭
  4. read-only SQLite の既存 predictions / races
  いずれも既存値のみ。合成しない。

出力
  C:\Users\Mr.me\Downloads\production_prediction_path_smoke_readonly_20260910_output_<ts>.txt
