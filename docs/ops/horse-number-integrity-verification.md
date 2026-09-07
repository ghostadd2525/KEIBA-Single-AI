# Horse Number Integrity — 検証レポート

**日付:** 2026-07-25  
**対象:** `race_refresh` Feature CSV 再発防止ゲート  
**範囲:** Prediction / Board / UI / Conversation / Knowledge / Memory 非変更

## 実装要約

1. `pi_keibanet/horse_number_integrity.py` — レース単位の馬番検証
2. `race_refresh.write_daily_features` — 正式馬番未取得レースは Feature 生成せず purge
3. 完了時ログ: `Race Refresh Incomplete` / `Horse Number Not Ready` / `Frame Number Not Ready`
4. レポート: `horse_number_integrity_latest.json`
5. Ops Health: `Horse Number Integrity`（PI probe `pi_horse_number_integrity` / ALT-E10）

## 確認ケース

### 正常系 — horse_number 取得済み

- 入力: `horse_id` + `horse_number` + `horse_number_source=umaban`
- 期待: integrity `ok=true`、`build_features` が呼ばれ Feature CSV に行が残る
- 結果: **PASS**（unit + EC2 `GET /v1/ops/horse-number-integrity?date=2026-07-26` → `ok=true`, ready=36）

### 異常系 — horse_number 未取得

- 入力: `horse_number=null`（display_order のみ）
- 期待: integrity `ok=false`、Feature 生成中止、既存の当該 race_id Feature 行を purge、ログに `Horse Number Not Ready`
- 結果: **PASS**（`test_missing_horse_number_skips_feature_generation`）

### 異常系 — fallback source

- 入力: `horse_number_source=fallback`
- 期待: Feature 生成対象外
- 結果: **PASS**（`test_blocked_when_fallback_source`）

## 本番スモーク（2026-07-25）

| 項目 | 結果 |
|------|------|
| EC2 unit tests | 5/5 OK |
| PI restart | OK |
| `/v1/ops/horse-number-integrity?date=2026-07-26` | HTTP 200, `ok=true`, blocked=`[]` |

## 運用メモ

- runners.csv 自体は馬番未確定でも保存する（後続 refresh で再取得）
- Feature CSV のみゲートする
- `frame_number` 未取得は警告ログのみ（hard gate は馬番）

