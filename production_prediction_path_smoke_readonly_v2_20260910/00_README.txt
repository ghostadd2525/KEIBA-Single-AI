Production Single-AI 予想経路 read-only smoke v2
==============================================

v1 (production_prediction_path_smoke_readonly_20260910) は実行しない。
v1 は read-only DB の過去 race_id で live detail GET し得る。

Cursor は内部 :8000 に接続しない。Production は変更しない。
POST /v1/prediction-runs は呼ばない。PR #23 は merge 禁止。

実行
  02_powershell\OWNER_READONLY.ps1

許可 HTTP（remote loopback のみ）
  GET http://127.0.0.1:8000/health
  GET http://127.0.0.1:8000/v1/predictions
  GET http://127.0.0.1:8000/v1/predictions/{race_id}
    race_id は同じ実行の list GET が返した値だけ

一覧が空
  DETAIL_GET_SKIPPED=NO_CURRENT_RACE
  detail GET しない

一覧が 5xx / timeout / 過大負荷
  そこで停止。detail GET しない

DB
  predictions 行数の SELECT COUNT のみ（GET 前後）
  race_id 選定には使わない

ファイル
  GET 前後で既存 var/logs/cache/db(-wal/-shm) の新規・サイズ変化を比較
  監査スクリプト自身はファイルを作らない

出力
  C:\Users\Mr.me\Downloads\production_prediction_path_smoke_readonly_v2_20260910_output_<ts>.txt
