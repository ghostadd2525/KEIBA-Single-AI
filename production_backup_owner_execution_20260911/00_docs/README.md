# Production backup Owner execution pack (作成のみ / 未実行)

このパックは **backup だけ** を行う Owner 実行手順です。
独立レビュー済み backup v2 contract を byte-identical で同梱します。

## まだ実行しない

- `PRODUCTION_BACKUP_EXECUTION_ALLOWED=NO`
- `PRODUCTION_BACKUP_EXECUTED=NO`
- `OWNER_PRODUCTION_BACKUP_APPROVED=NO`
- Owner が明示承認するまで `owner_backup.py` は Production source を開きません。
- このパックは 022 migration / systemd / env / POST 有効化を含みません。

## 正本

| 項目 | 値 |
|---|---|
| source | `/home/ubuntu/KEIBA-Single-AI/services/win5-ai/var/expect_ai.db` |
| source open | `file:<path>?mode=ro` + `PRAGMA query_only=ON` |
| dest | `--dest-root` 配下の UTC timestamp 専用 directory |
| dest dir mode | `0700` |
| dest file mode | `0600` |
| contract SHA256 | `55890bbdff280548c43bb53f80930049e83ba16fb7d2abe2b7c1c7e34b91c66e` |
| reviewed v2 ZIP SHA256 | `9653f26224679d750ea1c3f578a0b8dda0e2178dab5b8ad464ee8cf9a42b9a5a` |

dest-root は source の親 (`.../services/win5-ai/var`) にしてはいけません。
推奨: `/home/ubuntu/KEIBA-Single-AI/var/sqlite_backups`

## 成功判定

backup 成功時のみ:

- `BACKUP_STATUS=SUCCESS`
- `BACKUP_INTEGRITY_OK=YES`
- `BACKUP_SCHEMA_OK=YES`
- `BACKUP_MIGRATION_SET_OK=YES`
- `BACKUP_SHA256_OK=YES`
- `BACKUP_DISTINCT_INODE=YES`
- `MIGRATION_MAY_PROCEED=YES` （backup 成功の意味。022 実行許可ではない）

失敗時:

- `MIGRATION_MAY_PROCEED=NO`
- `APPLY_FORBIDDEN_AFTER_BACKUP_FAIL=YES`
- 022 APPLY 禁止

## 禁止

- source DB 内容変更
- 022 / migrate() / service 変更との同時実行
- 既存 ZIP 上書き
- claimed rehearsal v1 ZIP の再利用
- PR #23〜#29 の merge
