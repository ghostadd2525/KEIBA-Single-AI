# Collector C-8 — Production Readiness

**Date:** 2026-07-21  
**Scope:** Go-Live Must 解消（Retry / Budget SoT / Weekday Distribution）  
**Evidence:** `services/win5-ai/tests/ops/test_collect_c8.py`  
**Collector 責務:** 変更なし（取得→検証→状態更新の範囲内で retry_after を付与）

---

## 結論

| Must | 結果 |
|------|------|
| Must-1 Retry Automation | **PASS** |
| Must-2 Budget Source of Truth | **PASS** |
| Must-3 Weekday Distribution | **PASS** |

| 判定 | 結果 |
|------|------|
| C-8 Production Readiness | **PASS** |
| 本番 Go-Live | **HOLD**（Real KeibaNet 接続検証のみ残存・C-7 Must） |

---

## Must-1 Retry Automation

- Contract: `contracts/retry.py`（`next_business_day` / `compute_retry_after`）
- FAILED / PARTIAL 確定時に `retry_after` を自動設定
- `CollectRetry` は変更なしで `retry_after ≤ as_of` → PENDING

検証: FAILED → retry_after → CollectRetry → PENDING（PARTIAL も同様）

---

## Must-2 Budget Source of Truth

- **正本:** `CollectBudget`（`EXPECT_COLLECT_DAILY_LIMIT`、既定 150）
- `KeibaNetClient` は独自カウンタを廃止し、同一 `CollectBudget` を参照
- consume は Scheduler.dequeue、Client は remaining 検査のみ
- Manifest / Scheduler / Client の `daily_limit` / `used` / `remaining` が一致

---

## Must-3 Weekday Distribution

- Contract: `contracts/weekday_distribution.py`
- `scheduled_for` 未指定時、WEEKDAY artifact を week_id 直前の **月〜金**へ割当
- アルゴリズム: 最小負荷優先（1 日上限 = `daily_limit`、超過時は積み増し）
- RACE_DAY → `race_date` / AFTER_DRAW → `context.as_of` / 明示 `scheduled_for` → 固定

実測（72 race_meta）:

```
Mon 15 / Tue 15 / Wed 14 / Thu 14 / Fri 14
```

---

## 設計との差分

| 設計 | C-8 |
|------|-----|
| PARTIAL/FAILED → 翌営業日 retry | 実装（Retry Policy） |
| daily_limit 150 SoT | CollectBudget 一本化 |
| 月〜金分散 Collect | Planner/Queue で計画分散 |
| Real KeibaNet | 未実施（Go-Live HOLD 理由） |

---

## Go-Live 判定

**HOLD**

理由: C-8 Must は解消済みだが、C-7 残件の **Real KeibaNet Validation**（`EXPECT_KEIBANET_BASE_URL`）が未実施のため、本番投入は保留。

再現:

```bash
cd services/win5-ai
python -m unittest tests.ops.test_collect_c8 -v
```
