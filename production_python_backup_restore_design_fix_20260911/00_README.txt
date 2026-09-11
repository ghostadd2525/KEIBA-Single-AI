Python sqlite3.Connection.backup / restore design fix
=====================================================

PACK=production_python_backup_restore_design_fix_20260911
THIS IS NOT A PRODUCTION BACKUP EXECUTION PACK.

独立確認 BACKUP_DESIGN_REVIEW=CHANGES_REQUIRED への設計修正です。
v1 ZIP production_python_backup_restore_rehearsal_20260911.zip
(SHA256=ba896e345231e69ca7203d27ee312470786bcb969ad6818618ff13fbef7f1f6f)
は上書きしません。

このパックで行うこと
  隔離 temp DB だけで backup_contract を再検証する
  Owner には live schema inventory pack だけを実行させる
  v5 022 rebase と backup rehearsal は Production で実行しない
  Production 実行 pack は同梱しない

このパックで行わないこと
  Production / live DB / env / systemd への接続や変更
  PR #23〜#27 の更新・merge
  既存 review / DRY_RUN / rehearsal / inventory ZIP の上書き
  OWNER_PRODUCTION_BACKUP_APPROVED のセット
  persist 019/022 の Production 適用

合格条件（設計）
  1. source は file:<path>?mode=ro + uri=True + PRAGMA query_only=ON
  2. dest directory 0700 / backup DB 0600 を固定し検証
  3. PRODUCTION_BACKUP_EXECUTED=YES は Production source を実際に
     backup したときだけ。設計試験は常に NO
  4. 失敗時は MIGRATION_MAY_PROCEED=NO。明示した単一 dest
     （と SQLite sidecar）だけ削除または quarantine。source は触らない
  5. sqlite_master の table/index/trigger/view を canonical 化して SHA 比較
  6. schema_migrations + table/index/trigger/view 集合が一致
  7. source path の dev/ino を open 前後で確認
  8. dest が source と同一 path/inode でないこと
  9. WAL 中の committed snapshot だけを backup できること
  10. 同梱テストは bundle 単体で再実行可能（/workspace リポジトリ非依存）
  11. overwrite / 容量不足 / integrity failure / schema mismatch /
      permission mismatch の反例を同梱

再実行
  python3 run_tests.py
  または sh 04_run_local.sh

Owner schema inventory 返却後に live schema へ rehearsal fixture を合わせる。
現時点では LIVE_SCHEMA_EXACT_COMPATIBILITY=UNCONFIRMED。
