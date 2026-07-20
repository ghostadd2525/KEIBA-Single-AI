# 本番リリース前チェックリスト

Phase F — Operational Readiness

リリース前に以下をすべて確認してください。

---

## 1. Migration

- [ ] `python -m app.data.import_csv migrate` 実行
- [ ] 期待 migration が適用済み（001_init, 002_race_identity, 003_supply_platform）
- [ ] `GET /health` で db パス確認

---

## 2. ETL

- [ ] 対象開催日の CSV / データソース準備完了
- [ ] `POST /v1/admin/etl/schedule` または CLI `schedule YYYY-MM-DD` 成功
- [ ] `GET /v1/admin/etl/status` → status=success
- [ ] `etl_steps` 全ステップ success（download〜validation）

---

## 3. Coverage

- [ ] `GET /v1/data/coverage` 確認
- [ ] `race_total` が期待カタログ数と一致
- [ ] `missing_races` / `missing_features` が許容範囲内

---

## 4. real_ai 率 / mock 率

- [ ] `real_ai` 件数が期待値以上
- [ ] `mock` 件数と `by_reason` を確認
- [ ] 意図しない `mock_fallback` 増加がない

---

## 5. Health

- [ ] `GET /health` → `{"status":"ok"}`
- [ ] `expect-ai` systemd active
- [ ] `cloudflared-expect-ai` active（本番 tunnel 使用時）
- [ ] `https://ai.expect-keiba.com/health` 到達（本番）

---

## 6. API 動作

- [ ] `GET /v1/predictions` — provider=python
- [ ] `GET /v1/diagnostics/missing` — summary 取得
- [ ] `POST /v1/conversation/chat` — 正常応答
- [ ] `GET /v1/admin/monitoring` — alerts 確認

---

## 7. テスト

- [ ] `python -m unittest discover -s tests/ops -p "test_*.py" -v` 全 PASS
- [ ] 回帰テスト baseline 更新が意図的変更のみ

---

## 8. Performance

- [ ] `python scripts/ops/measure_baseline.py` 実行
- [ ] `tests/ops/baseline.json` と前回比較（p95 大幅悪化なし）

---

## 9. Backup

- [ ] SQLite DB バックアップ（`expect_ai.db`）
- [ ] platform/data CSV バックアップ
- [ ] 環境変数ファイル（`.env`）バックアップ

---

## 10. Rollback

- [ ] 前バージョン commit ID を記録
- [ ] `git checkout <prev>` + systemd restart 手順確認
- [ ] DB rollback 方針（migration 不可逆の場合は DB リストア）

---

## 署名

| 項目 | 値 |
|------|-----|
| 反映 commit | |
| 実施者 | |
| 実施日 | |
| Coverage % | |
| real_ai / mock | |
| 備考 | |
