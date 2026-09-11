Owner read-only live schema inventory
====================================

PACK=production_live_schema_inventory_readonly_20260911
THIS IS NOT APPLY.
HTTP なし。GET /health もしない（migrate() が書き込み得るため）。
Production DB は file: mode=ro + PRAGMA query_only のみ。

取得
  schema_migrations.version
  predictions CREATE TABLE / PRAGMA table_info / index_list / index_info
  predictions 関連 index/trigger の sqlite_master.sql
  conversation_history / race_results / race_evaluations の CREATE TABLE
  PRAGMA user_version / schema_version / SQLite version
  DB path / dev / ino / size / mtime

出さない
  行本文、bundle_json 値、race_id 値、馬名

実行
  02_powershell\OWNER_READONLY.ps1

PRODUCTION_SCHEMA_EXACTLY_REHEARSED=NO のまま
（Owner がこのパックを返すまで現行 live schema は未確定）
PRODUCTION_APPLY_READY=NO
