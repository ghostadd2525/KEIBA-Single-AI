Python sqlite3.Connection.backup / restore rehearsal
===================================================

PACK=production_python_backup_restore_rehearsal_20260911
THIS IS NOT A PRODUCTION BACKUP.

必須ゲート
  明示的な単一 --src
  source dev/ino/size/mtime
  dest は新規 timestamp ファイル
  既存 dest 上書き禁止
  dest parent 空き容量
  backup 後 PRAGMA integrity_check=ok
  schema_version / user_version / table count / schema_migrations 比較
  SHA256 / size / mode 記録
  bundle_json 等をログに出さない
  backup 失敗時 MIGRATION_MAY_PROCEED=NO
  restore は別 temp DB のみ。live へ復元しない
  Production backup は OWNER_PRODUCTION_BACKUP_APPROVED まで実行しない

このパックは ALLOW_LOCAL_SQLITE_BACKUP=1 の隔離 DB だけで検証する。
PRODUCTION_BACKUP_EXECUTED=NO
PRODUCTION_APPLY_READY=NO
